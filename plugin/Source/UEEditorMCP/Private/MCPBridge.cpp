// Copyright (c) 2025 zolnoor. All rights reserved.

#include "MCPBridge.h"
#include "ActionRegistry.h"
#include "MCPServer.h"
#include "Actions/EditorAction.h"

UUEEditorBridge::UUEEditorBridge()
	: Server(nullptr)
{
}

void UUEEditorBridge::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	UE_LOG(LogMCP, Log, TEXT("UEEditorMCP: Bridge initializing"));

	// Register action handlers
	RegisterActions();

	// Start the TCP server
	Server = new FEditorCommandServer(this, DefaultPort);
	if (Server->Start())
	{
		UE_LOG(LogMCP, Log, TEXT("UEEditorMCP: Server started on port %d"), DefaultPort);
	}
	else
	{
		UE_LOG(LogMCP, Error, TEXT("UEEditorMCP: Failed to start server"));
	}
}

void UUEEditorBridge::Deinitialize()
{
	UE_LOG(LogMCP, Log, TEXT("UEEditorMCP: Bridge deinitializing"));

	// Stop the server
	if (Server)
	{
		Server->Stop();
		delete Server;
		Server = nullptr;
	}

	// Clear action handlers
	ActionHandlers.Empty();

	Super::Deinitialize();
}

void UUEEditorBridge::RegisterActions()
{
	FUEEditorActionRegistry::RegisterDefaultActions(ActionHandlers);

	UE_LOG(LogMCP, Log, TEXT("UEEditorMCP: Registered %d action handlers"), ActionHandlers.Num());
}

TSharedRef<FEditorAction>* UUEEditorBridge::FindAction(const FString& CommandType)
{
	return ActionHandlers.Find(CommandType);
}

TSharedPtr<FJsonObject> UUEEditorBridge::ExecuteCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
	// =========================================================================
	// Action Handlers (modular actions - check these first)
	// =========================================================================
	TSharedRef<FEditorAction>* ActionPtr = FindAction(CommandType);
	if (ActionPtr)
	{
		return (*ActionPtr)->Execute(Params, Context);
	}

	// =========================================================================
	// Unknown Command (all handlers should be registered as actions now)
	// =========================================================================
	return CreateErrorResponse(
		FString::Printf(TEXT("Unknown command type: %s"), *CommandType),
		TEXT("unknown_command")
	);
}

TSharedPtr<FJsonObject> UUEEditorBridge::ExecuteCommandSafe(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
	// Phase 2: Top-level C++ exception guard around command execution.
	// SEH is handled per-action inside FEditorAction::ExecuteWithCrashProtection.
	try
	{
		return ExecuteCommandInternal(CommandType, Params);
	}
	catch (const std::exception& Ex)
	{
		UE_LOG(LogMCP, Error, TEXT("C++ exception in command '%s': %hs"), *CommandType, Ex.what());
		return CreateErrorResponse(
			FString::Printf(TEXT("C++ exception: %hs"), Ex.what()),
			TEXT("cpp_exception")
		);
	}
	catch (...)
	{
		UE_LOG(LogMCP, Error, TEXT("Unknown C++ exception in command '%s'"), *CommandType);
		return CreateErrorResponse(TEXT("Unknown C++ exception"), TEXT("cpp_exception"));
	}
}

TSharedPtr<FJsonObject> UUEEditorBridge::ExecuteCommandInternal(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
	return ExecuteCommand(CommandType, Params);
}

TSharedPtr<FJsonObject> UUEEditorBridge::CreateSuccessResponse(const TSharedPtr<FJsonObject>& ResultData)
{
	TSharedPtr<FJsonObject> Response = MakeShared<FJsonObject>();
	Response->SetStringField(TEXT("status"), TEXT("success"));
	Response->SetBoolField(TEXT("success"), true);

	if (ResultData.IsValid())
	{
		Response->SetObjectField(TEXT("result"), ResultData);
	}
	else
	{
		Response->SetObjectField(TEXT("result"), MakeShared<FJsonObject>());
	}

	return Response;
}

TSharedPtr<FJsonObject> UUEEditorBridge::CreateErrorResponse(const FString& ErrorMessage, const FString& ErrorType)
{
	TSharedPtr<FJsonObject> Response = MakeShared<FJsonObject>();
	Response->SetStringField(TEXT("status"), TEXT("error"));
	Response->SetBoolField(TEXT("success"), false);
	Response->SetStringField(TEXT("error"), ErrorMessage);
	Response->SetStringField(TEXT("error_type"), ErrorType);

	return Response;
}
