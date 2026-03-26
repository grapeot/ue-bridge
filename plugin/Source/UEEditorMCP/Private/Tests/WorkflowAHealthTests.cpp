#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Dom/JsonObject.h"
#include "Actions/EditorAction.h"
#include "Editor.h"
#include "EditorAssetLibrary.h"
#include "MCPBridge.h"
#include "Modules/ModuleManager.h"

namespace UEEditorMCP::Tests
{
constexpr auto EditorOnlyFlags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter;

UUEEditorBridge* GetBridge()
{
	return GEditor ? GEditor->GetEditorSubsystem<UUEEditorBridge>() : nullptr;
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
	UUEEditorBridge* Bridge = UEEditorMCP::Tests::GetBridge();
	TestNotNull(TEXT("UEEditorMCP bridge subsystem should resolve from GEditor"), Bridge);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPIsReadyCommandTest,
	"UEEditorMCP.Health.WorkflowA.IsReadyCommand",
	UEEditorMCP::Tests::EditorOnlyFlags)

bool FUEEditorMCPIsReadyCommandTest::RunTest(const FString& Parameters)
{
	UUEEditorBridge* Bridge = UEEditorMCP::Tests::GetBridge();
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
	UUEEditorBridge* Bridge = UEEditorMCP::Tests::GetBridge();
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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPGetPIEStateStoppedTest,
	"UEEditorMCP.Health.WorkflowA.GetPIEStateStopped",
	UEEditorMCP::Tests::EditorOnlyFlags)

bool FUEEditorMCPGetPIEStateStoppedTest::RunTest(const FString& Parameters)
{
	UUEEditorBridge* Bridge = UEEditorMCP::Tests::GetBridge();
	if (!TestNotNull(TEXT("UEEditorMCP bridge subsystem should resolve from GEditor"), Bridge))
	{
		return false;
	}

	TSharedPtr<FJsonObject> Response = Bridge->ExecuteCommand(TEXT("get_pie_state"), MakeShared<FJsonObject>());
	bool bSuccess = false;
	TestTrue(TEXT("get_pie_state should return success"), Response.IsValid() && Response->TryGetBoolField(TEXT("success"), bSuccess) && bSuccess);

	const TSharedPtr<FJsonObject>& ResultObject = UEEditorMCP::Tests::GetFlatSuccessObject(*this, Response);
	if (!ResultObject.IsValid())
	{
		return false;
	}

	FString State;
	bool bPlaySessionInProgress = true;
	TestTrue(TEXT("get_pie_state should expose state"), ResultObject->TryGetStringField(TEXT("state"), State));
	TestTrue(TEXT("get_pie_state should expose is_play_session_in_progress"), ResultObject->TryGetBoolField(TEXT("is_play_session_in_progress"), bPlaySessionInProgress));
	TestEqual(TEXT("PIE should be stopped in baseline automation run"), State, FString(TEXT("Stopped")));
	TestFalse(TEXT("No play session should be in progress during baseline state test"), bPlaySessionInProgress);

	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPLogControlSurfaceTest,
	"UEEditorMCP.Health.WorkflowA.LogControlSurface",
	UEEditorMCP::Tests::EditorOnlyFlags)

bool FUEEditorMCPLogControlSurfaceTest::RunTest(const FString& Parameters)
{
	UUEEditorBridge* Bridge = UEEditorMCP::Tests::GetBridge();
	if (!TestNotNull(TEXT("UEEditorMCP bridge subsystem should resolve from GEditor"), Bridge))
	{
		return false;
	}

	TSharedPtr<FJsonObject> ClearParams = MakeShared<FJsonObject>();
	ClearParams->SetStringField(TEXT("tag"), TEXT("workflow_a_log_control_surface"));
	TSharedPtr<FJsonObject> ClearResponse = Bridge->ExecuteCommand(TEXT("clear_logs"), ClearParams);
	bool bClearSuccess = false;
	TestTrue(TEXT("clear_logs should return success"), ClearResponse.IsValid() && ClearResponse->TryGetBoolField(TEXT("success"), bClearSuccess) && bClearSuccess);

	const TSharedPtr<FJsonObject>& ClearResult = UEEditorMCP::Tests::GetFlatSuccessObject(*this, ClearResponse);
	if (!ClearResult.IsValid())
	{
		return false;
	}
	TestTrue(TEXT("clear_logs should return new_cursor"), ClearResult->HasField(TEXT("new_cursor")));

	TSharedPtr<FJsonObject> AssertParams = MakeShared<FJsonObject>();
	AssertParams->SetStringField(TEXT("since_cursor"), ClearResult->GetStringField(TEXT("new_cursor")));
	TArray<TSharedPtr<FJsonValue>> Assertions;
	TSharedPtr<FJsonObject> Assertion = MakeShared<FJsonObject>();
	Assertion->SetStringField(TEXT("keyword"), TEXT("workflow_a_keyword_that_should_not_exist"));
	Assertion->SetNumberField(TEXT("expected_count"), 1);
	Assertion->SetStringField(TEXT("comparison"), TEXT(">="));
	Assertions.Add(MakeShared<FJsonValueObject>(Assertion));
	AssertParams->SetArrayField(TEXT("assertions"), Assertions);

	TSharedPtr<FJsonObject> AssertResponse = Bridge->ExecuteCommand(TEXT("assert_log"), AssertParams);
	bool bAssertSuccess = false;
	TestTrue(TEXT("assert_log should return success-shaped response"), AssertResponse.IsValid() && AssertResponse->TryGetBoolField(TEXT("success"), bAssertSuccess) && bAssertSuccess);

	const TSharedPtr<FJsonObject>& AssertResult = UEEditorMCP::Tests::GetFlatSuccessObject(*this, AssertResponse);
	if (!AssertResult.IsValid())
	{
		return false;
	}

	FString Overall;
	double PassedCount = 0.0;
	double FailedCount = 0.0;
	TestTrue(TEXT("assert_log should expose overall field"), AssertResult->TryGetStringField(TEXT("overall"), Overall));
	TestEqual(TEXT("assert_log should report a failed assertion when the keyword is absent"), Overall, FString(TEXT("fail")));
	TestTrue(TEXT("assert_log should expose passed field"), AssertResult->TryGetNumberField(TEXT("passed"), PassedCount));
	TestTrue(TEXT("assert_log should expose failed field"), AssertResult->TryGetNumberField(TEXT("failed"), FailedCount));
	TestEqual(TEXT("assert_log should report zero passing assertions for absent keyword"), PassedCount, 0.0);
	TestTrue(TEXT("assert_log should report at least one failed assertion for absent keyword"), FailedCount >= 1.0);

	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPPIESmokeLifecycleTest,
	"UEEditorMCP.Health.WorkflowA.PIESmokeLifecycle",
	UEEditorMCP::Tests::EditorOnlyFlags)

bool FUEEditorMCPPIESmokeLifecycleTest::RunTest(const FString& Parameters)
{
	UUEEditorBridge* Bridge = UEEditorMCP::Tests::GetBridge();
	if (!TestNotNull(TEXT("UEEditorMCP bridge subsystem should resolve from GEditor"), Bridge))
	{
		return false;
	}

	auto QueryPieState = [Bridge]() -> TSharedPtr<FJsonObject>
	{
		return Bridge->ExecuteCommand(TEXT("get_pie_state"), MakeShared<FJsonObject>());
	};

	TSharedPtr<FJsonObject> StartParams = MakeShared<FJsonObject>();
	StartParams->SetStringField(TEXT("mode"), TEXT("SelectedViewport"));
	TSharedPtr<FJsonObject> StartResponse = Bridge->ExecuteCommand(TEXT("start_pie"), StartParams);
	bool bStartSuccess = false;
	TestTrue(TEXT("start_pie should return success"), StartResponse.IsValid() && StartResponse->TryGetBoolField(TEXT("success"), bStartSuccess) && bStartSuccess);

	bool bObservedRunning = false;
	for (int32 Attempt = 0; Attempt < 40; ++Attempt)
	{
		FPlatformProcess::Sleep(0.25f);
		TSharedPtr<FJsonObject> StateResponse = QueryPieState();
		bool bStateSuccess = false;
		if (!StateResponse.IsValid() || !StateResponse->TryGetBoolField(TEXT("success"), bStateSuccess) || !bStateSuccess)
		{
			continue;
		}
		const TSharedPtr<FJsonObject>& StateResult = UEEditorMCP::Tests::GetFlatSuccessObject(*this, StateResponse);
		if (!StateResult.IsValid())
		{
			continue;
		}

		FString State;
		bool bInProgress = false;
		StateResult->TryGetStringField(TEXT("state"), State);
		StateResult->TryGetBoolField(TEXT("is_play_session_in_progress"), bInProgress);
		if (State == TEXT("Running") || bInProgress)
		{
			bObservedRunning = true;
			break;
		}
	}
	TestTrue(TEXT("PIE smoke test should observe a running play session after start_pie"), bObservedRunning);

	TSharedPtr<FJsonObject> StopResponse = Bridge->ExecuteCommand(TEXT("stop_pie"), MakeShared<FJsonObject>());
	bool bStopSuccess = false;
	TestTrue(TEXT("stop_pie should return success"), StopResponse.IsValid() && StopResponse->TryGetBoolField(TEXT("success"), bStopSuccess) && bStopSuccess);

	bool bObservedStopped = false;
	for (int32 Attempt = 0; Attempt < 40; ++Attempt)
	{
		FPlatformProcess::Sleep(0.25f);
		TSharedPtr<FJsonObject> StateResponse = QueryPieState();
		bool bStateSuccess = false;
		if (!StateResponse.IsValid() || !StateResponse->TryGetBoolField(TEXT("success"), bStateSuccess) || !bStateSuccess)
		{
			continue;
		}
		const TSharedPtr<FJsonObject>& StateResult = UEEditorMCP::Tests::GetFlatSuccessObject(*this, StateResponse);
		if (!StateResult.IsValid())
		{
			continue;
		}

		FString State;
		bool bInProgress = true;
		StateResult->TryGetStringField(TEXT("state"), State);
		StateResult->TryGetBoolField(TEXT("is_play_session_in_progress"), bInProgress);
		if (State == TEXT("Stopped") || !bInProgress)
		{
			bObservedStopped = true;
			break;
		}
	}
	TestTrue(TEXT("PIE smoke test should observe the play session quiescing after stop_pie"), bObservedStopped);

	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPCreateAndCompileBlueprintTest,
	"UEEditorMCP.Blueprint.WorkflowA.CreateAndCompile",
	UEEditorMCP::Tests::EditorOnlyFlags)

bool FUEEditorMCPCreateAndCompileBlueprintTest::RunTest(const FString& Parameters)
{
	UUEEditorBridge* Bridge = UEEditorMCP::Tests::GetBridge();
	if (!TestNotNull(TEXT("UEEditorMCP bridge subsystem should resolve from GEditor"), Bridge))
	{
		return false;
	}

	const FString BlueprintName = FString::Printf(TEXT("AT_WorkflowA_BP_%s"), *FGuid::NewGuid().ToString(EGuidFormats::Digits));
	const FString BlueprintFolder = TEXT("/Game/UEBridgeAutomation");
	const FString BlueprintAssetPath = BlueprintFolder / BlueprintName;

	TSharedPtr<FJsonObject> CreateParams = MakeShared<FJsonObject>();
	CreateParams->SetStringField(TEXT("name"), BlueprintName);
	CreateParams->SetStringField(TEXT("parent_class"), TEXT("Actor"));
	CreateParams->SetStringField(TEXT("path"), BlueprintFolder);

	TSharedPtr<FJsonObject> CreateResponse = Bridge->ExecuteCommand(TEXT("create_blueprint"), CreateParams);
	bool bCreateSuccess = false;
	TestTrue(TEXT("create_blueprint should return success"), CreateResponse.IsValid() && CreateResponse->TryGetBoolField(TEXT("success"), bCreateSuccess) && bCreateSuccess);
	const TSharedPtr<FJsonObject>& CreateResult = UEEditorMCP::Tests::GetFlatSuccessObject(*this, CreateResponse);
	if (!CreateResult.IsValid())
	{
		return false;
	}
	TestEqual(TEXT("create_blueprint should return the created name"), CreateResult->GetStringField(TEXT("name")), BlueprintName);
	TestTrue(TEXT("created blueprint asset should exist on disk"), UEditorAssetLibrary::DoesAssetExist(BlueprintAssetPath));

	TSharedPtr<FJsonObject> CompileParams = MakeShared<FJsonObject>();
	CompileParams->SetStringField(TEXT("blueprint_name"), BlueprintName);
	TSharedPtr<FJsonObject> CompileResponse = Bridge->ExecuteCommand(TEXT("compile_blueprint"), CompileParams);
	bool bCompileSuccess = false;
	TestTrue(TEXT("compile_blueprint should return success"), CompileResponse.IsValid() && CompileResponse->TryGetBoolField(TEXT("success"), bCompileSuccess) && bCompileSuccess);
	const TSharedPtr<FJsonObject>& CompileResult = UEEditorMCP::Tests::GetFlatSuccessObject(*this, CompileResponse);
	if (!CompileResult.IsValid())
	{
		UEditorAssetLibrary::DeleteAsset(BlueprintAssetPath);
		return false;
	}

	bool bCompiled = false;
	double ErrorCount = -1.0;
	TestTrue(TEXT("compile_blueprint should expose compiled field"), CompileResult->TryGetBoolField(TEXT("compiled"), bCompiled));
	TestTrue(TEXT("compile_blueprint should expose error_count field"), CompileResult->TryGetNumberField(TEXT("error_count"), ErrorCount));
	TestTrue(TEXT("compiled blueprint should report compiled=true"), bCompiled);
	TestEqual(TEXT("compiled blueprint should have zero compile errors"), ErrorCount, 0.0);

	return true;
}

#endif
