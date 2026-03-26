#include "EditorCommandExecutor.h"

#include "Actions/EditorAction.h"
#include "MCPBridge.h"
#include "Async/Async.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
FString SerializeResponseObject(const TSharedPtr<FJsonObject>& Response)
{
	FString ResponseStr;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&ResponseStr);
	FJsonSerializer::Serialize(Response.ToSharedRef(), Writer);
	return ResponseStr;
}
}

FString FEditorCommandExecutor::ExecuteGetContext(UMCPBridge* Bridge)
{
	FString Result;
	FEvent* DoneEvent = FPlatformProcess::GetSynchEventFromPool(false);

	AsyncTask(ENamedThreads::GameThread, [Bridge, &Result, DoneEvent]()
	{
		struct FTriggerOnExit
		{
			FEvent* Event;
			~FTriggerOnExit() { Event->Trigger(); }
		} TriggerGuard{DoneEvent};

		if (!Bridge)
		{
			Result = TEXT("{\"status\":\"error\",\"error\":\"Bridge not available\"}");
			return;
		}

		try
		{
			TSharedPtr<FJsonObject> ContextJson = Bridge->GetContext().ToJson();

			TSharedPtr<FJsonObject> Response = MakeShared<FJsonObject>();
			Response->SetStringField(TEXT("status"), TEXT("success"));
			Response->SetObjectField(TEXT("result"), ContextJson);
			Result = SerializeResponseObject(Response);
		}
		catch (...)
		{
			UE_LOG(LogMCP, Error, TEXT("UEEditorMCP: Exception in ExecuteGetContext"));
			Result = TEXT("{\"status\":\"error\",\"error\":\"Exception during get_context\"}");
		}
	});

	DoneEvent->Wait();
	FPlatformProcess::ReturnSynchEventToPool(DoneEvent);
	return Result;
}

FString FEditorCommandExecutor::ExecuteCommand(UMCPBridge* Bridge, const FString& CommandType, TSharedPtr<FJsonObject> Params)
{
	auto Result = MakeShared<FString>();
	FEvent* DoneEvent = FPlatformProcess::GetSynchEventFromPool(false);
	auto bCallerWaiting = MakeShared<TAtomic<bool>>(true);

	AsyncTask(ENamedThreads::GameThread, [Bridge, CmdType = CommandType, Params, Result, DoneEvent, bCallerWaiting]()
	{
		struct FCleanupGuard
		{
			FEvent* Event;
			TSharedPtr<TAtomic<bool>> CallerWaiting;
			~FCleanupGuard()
			{
				Event->Trigger();
				if (!CallerWaiting->Load())
				{
					FPlatformProcess::ReturnSynchEventToPool(Event);
				}
			}
		} Guard{DoneEvent, bCallerWaiting};

		if (!Bridge)
		{
			*Result = TEXT("{\"status\":\"error\",\"error\":\"Bridge not available\"}");
			return;
		}

		TSharedPtr<FJsonObject> Response;
		try
		{
			Response = Bridge->ExecuteCommandSafe(CmdType, Params);
		}
		catch (...)
		{
			UE_LOG(LogMCP, Error, TEXT("UEEditorMCP: Unhandled exception in ExecuteCommandSafe for '%s'"), *CmdType);
		}

		if (Response.IsValid())
		{
			*Result = SerializeResponseObject(Response);
		}
		else
		{
			*Result = FString::Printf(
				TEXT("{\"status\":\"error\",\"error\":\"Command '%s' returned null response\"}"),
				*CmdType);
		}
	});

	static constexpr uint32 GameThreadTimeoutMs = 240000;
	if (!DoneEvent->Wait(GameThreadTimeoutMs))
	{
		UE_LOG(LogMCP, Error, TEXT("UEEditorMCP: Game thread execution timed out after %ds for command '%s'"),
			GameThreadTimeoutMs / 1000, *CommandType);
		bCallerWaiting->Store(false);
		return FString::Printf(
			TEXT("{\"status\":\"error\",\"error\":\"Game thread execution timed out after %ds for command: %s\"}"),
			GameThreadTimeoutMs / 1000, *CommandType);
	}

	FPlatformProcess::ReturnSynchEventToPool(DoneEvent);
	return MoveTemp(*Result);
}
