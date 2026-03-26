#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Dom/JsonObject.h"
#include "Editor.h"
#include "MCPBridge.h"
#include "Modules/ModuleManager.h"

namespace UEEditorMCP::Tests
{
constexpr auto EditorOnlyFlags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter;

UMCPBridge* GetBridge()
{
	return GEditor ? GEditor->GetEditorSubsystem<UMCPBridge>() : nullptr;
}

	const TSharedPtr<FJsonObject>& GetFlatSuccessObject(FAutomationTestBase& Test, const TSharedPtr<FJsonObject>& Response)
	{
		Test.TestNotNull(TEXT("Response should be valid"), Response.Get());
		Test.TestTrue(TEXT("Response should have success=true"), Response.IsValid() && Response->HasTypedField<EJson::Boolean>(TEXT("success")));
		return Response;
	}

	bool ReadBoolField(FAutomationTestBase& Test, const TSharedPtr<FJsonObject>& Response, const TCHAR* FieldName, bool& OutValue)
	{
		if (!Response.IsValid())
		{
			Test.AddError(TEXT("Response should be valid before reading fields"));
			return false;
		}
		const bool bOk = Response->TryGetBoolField(FieldName, OutValue);
		Test.TestTrue(FString::Printf(TEXT("Response should expose bool field '%s'"), FieldName), bOk);
		return bOk;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPModuleLoadedTest,
	"UEEditorMCP.Health.WorkflowA.ModuleLoaded",
	UEEditorMCP::Tests::EditorOnlyFlags)

bool FUEEditorMCPModuleLoadedTest::RunTest(const FString& Parameters)
{
	TestTrue(TEXT("UEEditorMCP module should be loaded in the host project"), FModuleManager::Get().IsModuleLoaded(TEXT("UEEditorMCP")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPBridgeAvailableTest,
	"UEEditorMCP.Health.WorkflowA.BridgeAvailable",
	UEEditorMCP::Tests::EditorOnlyFlags)

bool FUEEditorMCPBridgeAvailableTest::RunTest(const FString& Parameters)
{
	UMCPBridge* Bridge = UEEditorMCP::Tests::GetBridge();
	TestNotNull(TEXT("UEEditorMCP bridge subsystem should resolve from GEditor"), Bridge);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPIsReadyCommandTest,
	"UEEditorMCP.Health.WorkflowA.IsReadyCommand",
	UEEditorMCP::Tests::EditorOnlyFlags)

bool FUEEditorMCPIsReadyCommandTest::RunTest(const FString& Parameters)
{
	UMCPBridge* Bridge = UEEditorMCP::Tests::GetBridge();
	if (!TestNotNull(TEXT("UEEditorMCP bridge subsystem should resolve from GEditor"), Bridge))
	{
		return false;
	}

	TSharedPtr<FJsonObject> Response = Bridge->ExecuteCommand(TEXT("is_ready"), MakeShared<FJsonObject>());
	bool bSuccess = false;
	TestTrue(TEXT("is_ready command should report success"), Response.IsValid() && Response->TryGetBoolField(TEXT("success"), bSuccess) && bSuccess);

	const TSharedPtr<FJsonObject>& ResultObject = UEEditorMCP::Tests::GetFlatSuccessObject(*this, Response);
	if (!ResultObject.IsValid())
	{
		return false;
	}

	bool bEditorValid = false;
	bool bWorldReady = false;
	bool bAssetRegistryReady = false;
	bool bReady = false;

	UEEditorMCP::Tests::ReadBoolField(*this, ResultObject, TEXT("editor_valid"), bEditorValid);
	UEEditorMCP::Tests::ReadBoolField(*this, ResultObject, TEXT("world_ready"), bWorldReady);
	UEEditorMCP::Tests::ReadBoolField(*this, ResultObject, TEXT("asset_registry_ready"), bAssetRegistryReady);
	UEEditorMCP::Tests::ReadBoolField(*this, ResultObject, TEXT("ready"), bReady);
	TestTrue(TEXT("editor_valid should be true inside editor automation"), bEditorValid);

	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPWorkflowAHealthSurfaceTest,
	"UEEditorMCP.Health.WorkflowA.HealthSurface",
	UEEditorMCP::Tests::EditorOnlyFlags)

bool FUEEditorMCPWorkflowAHealthSurfaceTest::RunTest(const FString& Parameters)
{
	UMCPBridge* Bridge = UEEditorMCP::Tests::GetBridge();
	if (!TestNotNull(TEXT("UEEditorMCP bridge subsystem should resolve from GEditor"), Bridge))
	{
		return false;
	}

	TSharedPtr<FJsonObject> LogsResponse = Bridge->ExecuteCommand(TEXT("get_editor_logs"), MakeShared<FJsonObject>());
	bool bLogsSuccess = false;
	TestTrue(TEXT("get_editor_logs should return a success-shaped response"), LogsResponse.IsValid() && LogsResponse->TryGetBoolField(TEXT("success"), bLogsSuccess) && bLogsSuccess);

	const TSharedPtr<FJsonObject>& LogsResult = UEEditorMCP::Tests::GetFlatSuccessObject(*this, LogsResponse);
	if (!LogsResult.IsValid())
	{
		return false;
	}

	const TArray<TSharedPtr<FJsonValue>>* Lines = nullptr;
	TestTrue(TEXT("get_editor_logs result should include lines array"), LogsResult->TryGetArrayField(TEXT("lines"), Lines));
	TestTrue(TEXT("get_editor_logs result should include total field"), LogsResult->HasField(TEXT("total")));
	TestTrue(TEXT("get_editor_logs result should include capturing field"), LogsResult->HasField(TEXT("capturing")));

	TSharedPtr<FJsonObject> InvalidResponse = Bridge->ExecuteCommand(TEXT("workflow_a_invalid_command"), MakeShared<FJsonObject>());
	bool bInvalidSuccess = true;
	FString ErrorType;
	TestTrue(TEXT("invalid command should return an error-shaped response"), InvalidResponse.IsValid() && InvalidResponse->TryGetBoolField(TEXT("success"), bInvalidSuccess) && !bInvalidSuccess);
	TestTrue(TEXT("invalid command should report unknown_command"), InvalidResponse.IsValid() && InvalidResponse->TryGetStringField(TEXT("error_type"), ErrorType) && ErrorType == TEXT("unknown_command"));

	return true;
}

#endif
