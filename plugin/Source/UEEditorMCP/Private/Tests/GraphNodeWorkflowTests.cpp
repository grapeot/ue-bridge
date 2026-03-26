#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Actions/EditorAction.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "EditorAssetLibrary.h"
#include "MCPBridge.h"

namespace UEEditorMCP::NodeTests
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

const TSharedPtr<FJsonObject>* FindPinByName(const TArray<TSharedPtr<FJsonValue>>& Pins, const FString& PinName)
{
	for (const TSharedPtr<FJsonValue>& PinValue : Pins)
	{
		const TSharedPtr<FJsonObject>* PinObject = nullptr;
		if (!PinValue->TryGetObject(PinObject) || !PinObject || !PinObject->IsValid())
		{
			continue;
		}
		FString CurrentPinName;
		if ((*PinObject)->TryGetStringField(TEXT("name"), CurrentPinName) && CurrentPinName == PinName)
		{
			return PinObject;
		}
	}
	return nullptr;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUEEditorMCPGraphNodeWorkflowTest,
	"UEEditorMCP.Graph.WorkflowA.CreateConnectDelete",
	UEEditorMCP::NodeTests::EditorOnlyFlags)

bool FUEEditorMCPGraphNodeWorkflowTest::RunTest(const FString& Parameters)
{
	UMCPBridge* Bridge = UEEditorMCP::NodeTests::GetBridge();
	if (!TestNotNull(TEXT("UEEditorMCP bridge subsystem should resolve from GEditor"), Bridge))
	{
		return false;
	}

	const FString BlueprintName = FString::Printf(TEXT("AT_NodeWorkflow_BP_%s"), *FGuid::NewGuid().ToString(EGuidFormats::Digits));
	const FString BlueprintFolder = TEXT("/Game/UEBridgeAutomation");
	const FString BlueprintAssetPath = BlueprintFolder / BlueprintName;

	TSharedPtr<FJsonObject> CreateParams = MakeShared<FJsonObject>();
	CreateParams->SetStringField(TEXT("name"), BlueprintName);
	CreateParams->SetStringField(TEXT("parent_class"), TEXT("Actor"));
	CreateParams->SetStringField(TEXT("path"), BlueprintFolder);

	TSharedPtr<FJsonObject> CreateResponse = Bridge->ExecuteCommand(TEXT("create_blueprint"), CreateParams);
	bool bCreateSuccess = false;
	TestTrue(TEXT("create_blueprint should succeed for graph workflow test"), CreateResponse.IsValid() && CreateResponse->TryGetBoolField(TEXT("success"), bCreateSuccess) && bCreateSuccess);
	if (!bCreateSuccess)
	{
		return false;
	}

	TSharedPtr<FJsonObject> BranchParams = MakeShared<FJsonObject>();
	BranchParams->SetStringField(TEXT("blueprint_name"), BlueprintName);
	TSharedPtr<FJsonObject> BranchResponse = Bridge->ExecuteCommand(TEXT("add_blueprint_branch_node"), BranchParams);
	bool bBranchSuccess = false;
	TestTrue(TEXT("add_blueprint_branch_node should succeed"), BranchResponse.IsValid() && BranchResponse->TryGetBoolField(TEXT("success"), bBranchSuccess) && bBranchSuccess);
	const TSharedPtr<FJsonObject>& BranchResult = UEEditorMCP::NodeTests::GetFlatSuccessObject(*this, BranchResponse);
	const FString BranchNodeId = BranchResult->GetStringField(TEXT("node_id"));

	TSharedPtr<FJsonObject> FunctionParams = MakeShared<FJsonObject>();
	FunctionParams->SetStringField(TEXT("blueprint_name"), BlueprintName);
	FunctionParams->SetStringField(TEXT("target"), TEXT("KismetSystemLibrary"));
	FunctionParams->SetStringField(TEXT("function_name"), TEXT("PrintString"));
	TSharedPtr<FJsonObject> FunctionResponse = Bridge->ExecuteCommand(TEXT("add_blueprint_function_node"), FunctionParams);
	bool bFunctionSuccess = false;
	TestTrue(TEXT("add_blueprint_function_node should succeed"), FunctionResponse.IsValid() && FunctionResponse->TryGetBoolField(TEXT("success"), bFunctionSuccess) && bFunctionSuccess);
	const TSharedPtr<FJsonObject>& FunctionResult = UEEditorMCP::NodeTests::GetFlatSuccessObject(*this, FunctionResponse);
	const FString FunctionNodeId = FunctionResult->GetStringField(TEXT("node_id"));

	TSharedPtr<FJsonObject> BranchPinsParams = MakeShared<FJsonObject>();
	BranchPinsParams->SetStringField(TEXT("blueprint_name"), BlueprintName);
	BranchPinsParams->SetStringField(TEXT("node_id"), BranchNodeId);
	TSharedPtr<FJsonObject> BranchPinsResponse = Bridge->ExecuteCommand(TEXT("get_node_pins"), BranchPinsParams);
	bool bBranchPinsSuccess = false;
	TestTrue(TEXT("get_node_pins should succeed for branch node"), BranchPinsResponse.IsValid() && BranchPinsResponse->TryGetBoolField(TEXT("success"), bBranchPinsSuccess) && bBranchPinsSuccess);
	const TSharedPtr<FJsonObject>& BranchPinsResult = UEEditorMCP::NodeTests::GetFlatSuccessObject(*this, BranchPinsResponse);
	const TArray<TSharedPtr<FJsonValue>>* BranchPins = nullptr;
	TestTrue(TEXT("branch pins response should include pins array"), BranchPinsResult->TryGetArrayField(TEXT("pins"), BranchPins));
	TestNotNull(TEXT("branch node should expose Then pin"), UEEditorMCP::NodeTests::FindPinByName(*BranchPins, TEXT("Then")));

	TSharedPtr<FJsonObject> FunctionPinsParams = MakeShared<FJsonObject>();
	FunctionPinsParams->SetStringField(TEXT("blueprint_name"), BlueprintName);
	FunctionPinsParams->SetStringField(TEXT("node_id"), FunctionNodeId);
	TSharedPtr<FJsonObject> FunctionPinsResponse = Bridge->ExecuteCommand(TEXT("get_node_pins"), FunctionPinsParams);
	bool bFunctionPinsSuccess = false;
	TestTrue(TEXT("get_node_pins should succeed for function node"), FunctionPinsResponse.IsValid() && FunctionPinsResponse->TryGetBoolField(TEXT("success"), bFunctionPinsSuccess) && bFunctionPinsSuccess);
	const TSharedPtr<FJsonObject>& FunctionPinsResult = UEEditorMCP::NodeTests::GetFlatSuccessObject(*this, FunctionPinsResponse);
	const TArray<TSharedPtr<FJsonValue>>* FunctionPins = nullptr;
	TestTrue(TEXT("function pins response should include pins array"), FunctionPinsResult->TryGetArrayField(TEXT("pins"), FunctionPins));
	TestNotNull(TEXT("function node should expose execute pin"), UEEditorMCP::NodeTests::FindPinByName(*FunctionPins, TEXT("execute")));

	TSharedPtr<FJsonObject> ConnectParams = MakeShared<FJsonObject>();
	ConnectParams->SetStringField(TEXT("blueprint_name"), BlueprintName);
	ConnectParams->SetStringField(TEXT("source_node_id"), BranchNodeId);
	ConnectParams->SetStringField(TEXT("source_pin"), TEXT("Then"));
	ConnectParams->SetStringField(TEXT("target_node_id"), FunctionNodeId);
	ConnectParams->SetStringField(TEXT("target_pin"), TEXT("execute"));
	TSharedPtr<FJsonObject> ConnectResponse = Bridge->ExecuteCommand(TEXT("connect_blueprint_nodes"), ConnectParams);
	bool bConnectSuccess = false;
	TestTrue(TEXT("connect_blueprint_nodes should succeed"), ConnectResponse.IsValid() && ConnectResponse->TryGetBoolField(TEXT("success"), bConnectSuccess) && bConnectSuccess);

	TSharedPtr<FJsonObject> FunctionPinsAfterConnectResponse = Bridge->ExecuteCommand(TEXT("get_node_pins"), FunctionPinsParams);
	bool bFunctionPinsAfterConnectSuccess = false;
	TestTrue(TEXT("get_node_pins should still succeed after connection"), FunctionPinsAfterConnectResponse.IsValid() && FunctionPinsAfterConnectResponse->TryGetBoolField(TEXT("success"), bFunctionPinsAfterConnectSuccess) && bFunctionPinsAfterConnectSuccess);
	const TSharedPtr<FJsonObject>& FunctionPinsAfterConnectResult = UEEditorMCP::NodeTests::GetFlatSuccessObject(*this, FunctionPinsAfterConnectResponse);
	const TArray<TSharedPtr<FJsonValue>>* FunctionPinsAfterConnect = nullptr;
	TestTrue(TEXT("function pins response should include pins array after connect"), FunctionPinsAfterConnectResult->TryGetArrayField(TEXT("pins"), FunctionPinsAfterConnect));
	const TSharedPtr<FJsonObject>* ExecutePin = UEEditorMCP::NodeTests::FindPinByName(*FunctionPinsAfterConnect, TEXT("execute"));
	TestNotNull(TEXT("execute pin should still exist after connection"), ExecutePin);
	if (ExecutePin && *ExecutePin)
	{
		const TArray<TSharedPtr<FJsonValue>>* LinkedTo = nullptr;
		TestTrue(TEXT("execute pin should expose linked_to array"), (*ExecutePin)->TryGetArrayField(TEXT("linked_to"), LinkedTo));
		TestTrue(TEXT("execute pin should have at least one incoming link after connect"), LinkedTo && LinkedTo->Num() > 0);
	}

	TSharedPtr<FJsonObject> DeleteParams = MakeShared<FJsonObject>();
	DeleteParams->SetStringField(TEXT("blueprint_name"), BlueprintName);
	DeleteParams->SetStringField(TEXT("node_id"), FunctionNodeId);
	TSharedPtr<FJsonObject> DeleteResponse = Bridge->ExecuteCommand(TEXT("delete_blueprint_node"), DeleteParams);
	bool bDeleteSuccess = false;
	TestTrue(TEXT("delete_blueprint_node should succeed"), DeleteResponse.IsValid() && DeleteResponse->TryGetBoolField(TEXT("success"), bDeleteSuccess) && bDeleteSuccess);

	TSharedPtr<FJsonObject> DeletedNodePinsResponse = Bridge->ExecuteCommand(TEXT("get_node_pins"), FunctionPinsParams);
	bool bDeletedPinsSuccess = true;
	TestTrue(TEXT("deleted node should no longer return a success-shaped pin response"), DeletedNodePinsResponse.IsValid() && DeletedNodePinsResponse->TryGetBoolField(TEXT("success"), bDeletedPinsSuccess) && !bDeletedPinsSuccess);

	return true;
}

#endif
