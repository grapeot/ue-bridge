#include "../../Public/Actions/AnimGraphActions.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimSequence.h"
#include "AnimGraphNode_StateMachineBase.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_StateResult.h"
#include "AnimGraphNode_ModifyBone.h"
#include "BoneControllers/AnimNode_ModifyBone.h"
#include "AnimStateEntryNode.h"
#include "AnimStateNode.h"
#include "AnimStateNodeBase.h"
#include "AnimStateTransitionNode.h"
#include "AnimationStateMachineGraph.h"
#include "AnimationStateMachineSchema.h"
#include "AnimationGraphSchema.h"

#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphSchema_K2.h"
#include "EdGraphSchema_K2_Actions.h"

#include "K2Node_CallFunction.h"
#include "K2Node_VariableGet.h"
#include "Kismet/KismetMathLibrary.h"

#include "EditorAssetLibrary.h"
#include "UObject/UnrealType.h"

namespace
{
	UAnimBlueprint* ResolveAnimBlueprint(UBlueprint* Blueprint, FString& OutError)
	{
		if (!Blueprint)
		{
			OutError = TEXT("Blueprint not found");
			return nullptr;
		}

		UAnimBlueprint* AnimBlueprint = Cast<UAnimBlueprint>(Blueprint);
		if (!AnimBlueprint)
		{
			OutError = FString::Printf(TEXT("Blueprint '%s' is not an Animation Blueprint"), *Blueprint->GetName());
			return nullptr;
		}

		return AnimBlueprint;
	}

	FString NormalizeGraphName(const FString& Name)
	{
		return Name.Replace(TEXT(" "), TEXT("_"));
	}

	FString GetStateNodeDisplayName(const UAnimStateNodeBase* StateNode)
	{
		if (!StateNode)
		{
			return TEXT("");
		}

		const FString Title = StateNode->GetNodeTitle(ENodeTitleType::FullTitle).ToString();
		if (!Title.IsEmpty())
		{
			return Title;
		}

		if (const UEdGraph* BoundGraph = StateNode->GetBoundGraph())
		{
			return BoundGraph->GetName();
		}

		return TEXT("");
	}

	FString GetStateNodeBoundGraphName(const UAnimStateNodeBase* StateNode)
	{
		if (!StateNode || !StateNode->GetBoundGraph())
		{
			return TEXT("");
		}

		return StateNode->GetBoundGraph()->GetName();
	}

	bool NamesMatch(const FString& A, const FString& B)
	{
		return A.Equals(B, ESearchCase::IgnoreCase);
	}

	FVector2D GetNodePositionFromParams(const TSharedPtr<FJsonObject>& Params)
	{
		FVector2D Position(0.0f, 0.0f);

		if (!Params.IsValid())
		{
			return Position;
		}

		FString PositionString;
		if (Params->TryGetStringField(TEXT("node_position"), PositionString) && !PositionString.IsEmpty())
		{
			TArray<FString> Parts;
			PositionString.Replace(TEXT("["), TEXT("")).Replace(TEXT("]"), TEXT("")).ParseIntoArray(Parts, TEXT(","));
			if (Parts.Num() >= 2)
			{
				Position.X = FCString::Atof(*Parts[0].TrimStartAndEnd());
				Position.Y = FCString::Atof(*Parts[1].TrimStartAndEnd());
			}
		}

		const TArray<TSharedPtr<FJsonValue>>* PositionArray = nullptr;
		if (Params->TryGetArrayField(TEXT("node_position"), PositionArray) && PositionArray && PositionArray->Num() >= 2)
		{
			Position.X = (*PositionArray)[0]->AsNumber();
			Position.Y = (*PositionArray)[1]->AsNumber();
		}

		return Position;
	}

	UAnimGraphNode_StateMachineBase* FindStateMachineNode(UAnimBlueprint* AnimBlueprint, const FString& StateMachineName, FString& OutError)
	{
		if (!AnimBlueprint)
		{
			OutError = TEXT("Animation Blueprint is null");
			return nullptr;
		}

		TArray<UEdGraph*> AllGraphs;
		AnimBlueprint->GetAllGraphs(AllGraphs);

		UAnimGraphNode_StateMachineBase* FirstStateMachine = nullptr;

		for (UEdGraph* Graph : AllGraphs)
		{
			if (!Graph)
			{
				continue;
			}

			for (UEdGraphNode* Node : Graph->Nodes)
			{
				UAnimGraphNode_StateMachineBase* StateMachineNode = Cast<UAnimGraphNode_StateMachineBase>(Node);
				if (!StateMachineNode || !StateMachineNode->EditorStateMachineGraph)
				{
					continue;
				}

				if (!FirstStateMachine)
				{
					FirstStateMachine = StateMachineNode;
				}

				if (StateMachineName.IsEmpty())
				{
					continue;
				}

				const FString Title = StateMachineNode->GetNodeTitle(ENodeTitleType::FullTitle).ToString();
				const FString GraphName = StateMachineNode->EditorStateMachineGraph->GetName();
				if (NamesMatch(Title, StateMachineName) || NamesMatch(GraphName, StateMachineName))
				{
					return StateMachineNode;
				}
			}
		}

		if (StateMachineName.IsEmpty())
		{
			if (FirstStateMachine)
			{
				return FirstStateMachine;
			}

			OutError = FString::Printf(TEXT("Animation Blueprint '%s' has no state machine"), *AnimBlueprint->GetName());
		}
		else
		{
			OutError = FString::Printf(TEXT("State machine '%s' not found in Animation Blueprint '%s'"), *StateMachineName, *AnimBlueprint->GetName());
		}

		return nullptr;
	}

	UAnimationStateMachineGraph* GetStateMachineGraph(UAnimBlueprint* AnimBlueprint, const FString& StateMachineName, FString& OutError)
	{
		UAnimGraphNode_StateMachineBase* StateMachineNode = FindStateMachineNode(AnimBlueprint, StateMachineName, OutError);
		return StateMachineNode ? StateMachineNode->EditorStateMachineGraph : nullptr;
	}

	UAnimStateNode* FindStateNodeByName(UAnimationStateMachineGraph* Graph, const FString& StateName)
	{
		if (!Graph)
		{
			return nullptr;
		}

		const FString NormalizedRequestedName = NormalizeGraphName(StateName);

		for (UEdGraphNode* Node : Graph->Nodes)
		{
			UAnimStateNode* StateNode = Cast<UAnimStateNode>(Node);
			if (!StateNode)
			{
				continue;
			}

			const FString DisplayName = GetStateNodeDisplayName(StateNode);
			const FString GraphName = GetStateNodeBoundGraphName(StateNode);
			if (NamesMatch(DisplayName, StateName)
				|| NamesMatch(DisplayName, NormalizedRequestedName)
				|| NamesMatch(GraphName, StateName)
				|| NamesMatch(GraphName, NormalizedRequestedName))
			{
				return StateNode;
			}
		}

		return nullptr;
	}

	UAnimStateTransitionNode* FindTransitionByEndpoints(UAnimationStateMachineGraph* Graph, const FString& FromState, const FString& ToState)
	{
		if (!Graph)
		{
			return nullptr;
		}

		for (UEdGraphNode* Node : Graph->Nodes)
		{
			UAnimStateTransitionNode* TransitionNode = Cast<UAnimStateTransitionNode>(Node);
			if (!TransitionNode)
			{
				continue;
			}

			const UAnimStateNodeBase* PreviousState = TransitionNode->GetPreviousState();
			const UAnimStateNodeBase* NextState = TransitionNode->GetNextState();
			if (!PreviousState || !NextState)
			{
				continue;
			}

			const bool bFromMatches = NamesMatch(GetStateNodeDisplayName(PreviousState), FromState)
				|| NamesMatch(GetStateNodeBoundGraphName(PreviousState), FromState)
				|| NamesMatch(GetStateNodeBoundGraphName(PreviousState), NormalizeGraphName(FromState));
			const bool bToMatches = NamesMatch(GetStateNodeDisplayName(NextState), ToState)
				|| NamesMatch(GetStateNodeBoundGraphName(NextState), ToState)
				|| NamesMatch(GetStateNodeBoundGraphName(NextState), NormalizeGraphName(ToState));

			if (bFromMatches && bToMatches)
			{
				return TransitionNode;
			}
		}

		return nullptr;
	}

	UEdGraphNode* FindTransitionResultNode(UEdGraph* RuleGraph)
	{
		if (!RuleGraph)
		{
			return nullptr;
		}

		for (UEdGraphNode* Node : RuleGraph->Nodes)
		{
			if (!Node)
			{
				continue;
			}

			if (Node->FindPin(FName(TEXT("bCanEnterTransition"))))
			{
				return Node;
			}
		}

		for (UEdGraphNode* Node : RuleGraph->Nodes)
		{
			if (Node && Node->GetClass()->GetName().Contains(TEXT("TransitionResult")))
			{
				return Node;
			}
		}

		return nullptr;
	}

	UEdGraphNode* FindStateResultNode(UEdGraph* StateGraph)
	{
		if (!StateGraph)
		{
			return nullptr;
		}

		for (UEdGraphNode* Node : StateGraph->Nodes)
		{
			if (!Node)
			{
				continue;
			}

			const FString ClassName = Node->GetClass()->GetName();
			if (ClassName.Contains(TEXT("Root")) || ClassName.Contains(TEXT("Result")))
			{
				return Node;
			}
		}

		return nullptr;
	}

	UEdGraphPin* FindFirstInputPin(UEdGraphNode* Node)
	{
		if (!Node)
		{
			return nullptr;
		}

		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin && Pin->Direction == EGPD_Input)
			{
				return Pin;
			}
		}

		return nullptr;
	}

	UEdGraphPin* FindFirstOutputPin(UEdGraphNode* Node)
	{
		if (!Node)
		{
			return nullptr;
		}

		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin && Pin->Direction == EGPD_Output)
			{
				return Pin;
			}
		}

		return nullptr;
	}

	bool IsBooleanBlueprintVariable(UAnimBlueprint* AnimBlueprint, const FString& VariableName)
	{
		if (!AnimBlueprint)
		{
			return false;
		}

		const FName VariableFName(*VariableName);

		for (const FBPVariableDescription& Variable : AnimBlueprint->NewVariables)
		{
			if (Variable.VarName == VariableFName && Variable.VarType.PinCategory == UEdGraphSchema_K2::PC_Boolean)
			{
				return true;
			}
		}

		auto HasBoolProperty = [&VariableFName](const UClass* Class) -> bool
		{
			for (const UClass* CurrentClass = Class; CurrentClass; CurrentClass = CurrentClass->GetSuperClass())
			{
				const FProperty* Property = FindFProperty<FProperty>(CurrentClass, VariableFName);
				if (Property && CastField<const FBoolProperty>(Property))
				{
					return true;
				}
			}
			return false;
		};

		return HasBoolProperty(AnimBlueprint->GeneratedClass)
			|| HasBoolProperty(AnimBlueprint->SkeletonGeneratedClass)
			|| HasBoolProperty(AnimBlueprint->ParentClass);
	}

	void ClearRuleGraph(UEdGraph* RuleGraph, UEdGraphNode* ResultNode)
	{
		if (!RuleGraph)
		{
			return;
		}

		TArray<UEdGraphNode*> NodesToRemove;
		for (UEdGraphNode* Node : RuleGraph->Nodes)
		{
			if (!Node || Node == ResultNode)
			{
				continue;
			}

			const FString ClassName = Node->GetClass()->GetName();
			if (ClassName.Contains(TEXT("Entry")))
			{
				continue;
			}

			NodesToRemove.Add(Node);
		}

		for (UEdGraphNode* Node : NodesToRemove)
		{
			RuleGraph->RemoveNode(Node);
		}
	}

	void ClearStateGraph(UEdGraph* StateGraph, UEdGraphNode* ResultNode)
	{
		if (!StateGraph)
		{
			return;
		}

		TArray<UEdGraphNode*> NodesToRemove;
		for (UEdGraphNode* Node : StateGraph->Nodes)
		{
			if (!Node || Node == ResultNode)
			{
				continue;
			}

			const FString ClassName = Node->GetClass()->GetName();
			if (ClassName.Contains(TEXT("Entry")))
			{
				continue;
			}

			NodesToRemove.Add(Node);
		}

		for (UEdGraphNode* Node : NodesToRemove)
		{
			StateGraph->RemoveNode(Node);
		}
	}

	TSharedPtr<FJsonValueObject> MakeStateJson(UAnimStateNode* StateNode)
	{
		TSharedPtr<FJsonObject> StateObject = MakeShared<FJsonObject>();
		StateObject->SetStringField(TEXT("state_name"), GetStateNodeDisplayName(StateNode));
		StateObject->SetStringField(TEXT("state_node_id"), StateNode->NodeGuid.ToString());
		StateObject->SetStringField(TEXT("bound_graph_name"), GetStateNodeBoundGraphName(StateNode));
		StateObject->SetStringField(TEXT("state_type"), TEXT("SingleAnimation"));
		return MakeShared<FJsonValueObject>(StateObject);
	}

	TSharedPtr<FJsonValueObject> MakeTransitionJson(UAnimStateTransitionNode* TransitionNode)
	{
		TSharedPtr<FJsonObject> TransitionObject = MakeShared<FJsonObject>();
		TransitionObject->SetStringField(TEXT("transition_node_id"), TransitionNode->NodeGuid.ToString());
		TransitionObject->SetStringField(TEXT("from_state"), GetStateNodeDisplayName(TransitionNode->GetPreviousState()));
		TransitionObject->SetStringField(TEXT("to_state"), GetStateNodeDisplayName(TransitionNode->GetNextState()));
		TransitionObject->SetStringField(TEXT("rule_graph_name"), TransitionNode->BoundGraph ? TransitionNode->BoundGraph->GetName() : TEXT(""));
		TransitionObject->SetNumberField(TEXT("crossfade_duration"), TransitionNode->CrossfadeDuration);
		TransitionObject->SetNumberField(TEXT("priority_order"), TransitionNode->PriorityOrder);
		return MakeShared<FJsonValueObject>(TransitionObject);
	}
}

bool FListAnimStatesAction::Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError)
{
	return ValidateBlueprint(Params, Context, OutError);
}

TSharedPtr<FJsonObject> FListAnimStatesAction::ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context)
{
	UBlueprint* Blueprint = GetTargetBlueprint(Params, Context);
	FString Error;
	UAnimBlueprint* AnimBlueprint = ResolveAnimBlueprint(Blueprint, Error);
	if (!AnimBlueprint)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: list_anim_states failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("invalid_blueprint_type"));
	}

	const FString RequestedStateMachineName = GetOptionalString(Params, TEXT("state_machine_name"));
	UAnimGraphNode_StateMachineBase* StateMachineNode = FindStateMachineNode(AnimBlueprint, RequestedStateMachineName, Error);
	if (!StateMachineNode || !StateMachineNode->EditorStateMachineGraph)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: list_anim_states failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("state_machine_not_found"));
	}

	UAnimationStateMachineGraph* StateMachineGraph = StateMachineNode->EditorStateMachineGraph;
	TArray<TSharedPtr<FJsonValue>> States;
	TArray<TSharedPtr<FJsonValue>> Transitions;
	FString EntryNodeId;

	for (UEdGraphNode* Node : StateMachineGraph->Nodes)
	{
		if (UAnimStateEntryNode* EntryNode = Cast<UAnimStateEntryNode>(Node))
		{
			EntryNodeId = EntryNode->NodeGuid.ToString();
		}
		else if (UAnimStateNode* StateNode = Cast<UAnimStateNode>(Node))
		{
			States.Add(MakeStateJson(StateNode));
		}
		else if (UAnimStateTransitionNode* TransitionNode = Cast<UAnimStateTransitionNode>(Node))
		{
			Transitions.Add(MakeTransitionJson(TransitionNode));
		}
	}

	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetStringField(TEXT("blueprint_name"), Blueprint->GetName());
	Result->SetStringField(TEXT("state_machine_name"), StateMachineGraph->GetName());
	Result->SetStringField(TEXT("state_machine_node_id"), StateMachineNode->NodeGuid.ToString());
	Result->SetStringField(TEXT("entry_node_id"), EntryNodeId);
	Result->SetArrayField(TEXT("states"), States);
	Result->SetArrayField(TEXT("transitions"), Transitions);

	UE_LOG(LogMCP, Log, TEXT("UEBridgeEditor: Listed %d states and %d transitions in state machine '%s' for AnimBP '%s'"),
		States.Num(), Transitions.Num(), *StateMachineGraph->GetName(), *Blueprint->GetName());

	return CreateSuccessResponse(Result);
}

bool FApplyCrouchPoseFixAction::Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError)
{
	return ValidateBlueprint(Params, Context, OutError);
}

TSharedPtr<FJsonObject> FApplyCrouchPoseFixAction::ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context)
{
	UBlueprint* Blueprint = GetTargetBlueprint(Params, Context);
	FString Error;
	UAnimBlueprint* AnimBlueprint = ResolveAnimBlueprint(Blueprint, Error);
	if (!AnimBlueprint)
	{
		return CreateErrorResponse(Error, TEXT("invalid_blueprint_type"));
	}

	const FString StateMachineName = GetOptionalString(Params, TEXT("state_machine_name"), TEXT("Locomotion"));
	const FString StateName = GetOptionalString(Params, TEXT("state_name"), TEXT("Crouch"));

	UAnimationStateMachineGraph* StateMachineGraph = GetStateMachineGraph(AnimBlueprint, StateMachineName, Error);
	if (!StateMachineGraph)
	{
		return CreateErrorResponse(Error, TEXT("state_machine_not_found"));
	}

	UAnimStateNode* StateNode = FindStateNodeByName(StateMachineGraph, StateName);
	if (!StateNode)
	{
		return CreateErrorResponse(FString::Printf(TEXT("State '%s' not found"), *StateName), TEXT("state_not_found"));
	}

	UEdGraph* StateGraph = StateNode->GetBoundGraph();
	if (!StateGraph)
	{
		return CreateErrorResponse(TEXT("State graph is invalid"), TEXT("state_graph_invalid"));
	}

	UAnimGraphNode_SequencePlayer* SequencePlayer = nullptr;
	UAnimGraphNode_StateResult* ResultNode = nullptr;
	TArray<UEdGraphNode*> NodesToRemove;

	for (UEdGraphNode* Node : StateGraph->Nodes)
	{
		if (UAnimGraphNode_SequencePlayer* SP = Cast<UAnimGraphNode_SequencePlayer>(Node))
		{
			SequencePlayer = SP;
		}
		else if (UAnimGraphNode_StateResult* SR = Cast<UAnimGraphNode_StateResult>(Node))
		{
			ResultNode = SR;
		}
		else if (Node)
		{
			NodesToRemove.Add(Node);
		}
	}

	if (!SequencePlayer || !ResultNode)
	{
		return CreateErrorResponse(TEXT("Could not find SequencePlayer or ResultNode in state graph"), TEXT("nodes_not_found"));
	}

	UEdGraphPin* ResultInputPin = FindFirstInputPin(ResultNode);
	if (ResultInputPin)
	{
		ResultInputPin->BreakAllPinLinks();
	}

	for (UEdGraphNode* Node : NodesToRemove)
	{
		if (!Node)
		{
			continue;
		}

		Node->BreakAllNodeLinks();
		StateGraph->RemoveNode(Node);
	}

	UAnimGraphNode_ModifyBone* PelvisNode = NewObject<UAnimGraphNode_ModifyBone>(StateGraph);
	StateGraph->AddNode(PelvisNode, false, false);
	PelvisNode->CreateNewGuid();
	PelvisNode->PostPlacedNewNode();
	PelvisNode->AllocateDefaultPins();
	PelvisNode->NodePosX = 300;
	PelvisNode->NodePosY = 0;
	PelvisNode->Node.BoneToModify.BoneName = FName(TEXT("pelvis"));
	PelvisNode->Node.Translation = FVector(0.0f, 0.0f, -45.0f);
	PelvisNode->Node.TranslationMode = BMM_Additive;
	PelvisNode->Node.TranslationSpace = BCS_ComponentSpace;

	UAnimGraphNode_ModifyBone* SpineNode = NewObject<UAnimGraphNode_ModifyBone>(StateGraph);
	StateGraph->AddNode(SpineNode, false, false);
	SpineNode->CreateNewGuid();
	SpineNode->PostPlacedNewNode();
	SpineNode->AllocateDefaultPins();
	SpineNode->NodePosX = 600;
	SpineNode->NodePosY = 0;
	SpineNode->Node.BoneToModify.BoneName = FName(TEXT("spine_01"));
	SpineNode->Node.Rotation = FRotator(15.0f, 0.0f, 0.0f);
	SpineNode->Node.RotationMode = BMM_Additive;
	SpineNode->Node.RotationSpace = BCS_ParentBoneSpace;

	const UEdGraphSchema* Schema = StateGraph->GetSchema();
	UEdGraphPin* SP_Output = FindFirstOutputPin(SequencePlayer);
	UEdGraphPin* Pelvis_Input = FindFirstInputPin(PelvisNode);
	UEdGraphPin* Pelvis_Output = FindFirstOutputPin(PelvisNode);
	UEdGraphPin* Spine_Input = FindFirstInputPin(SpineNode);
	UEdGraphPin* Spine_Output = FindFirstOutputPin(SpineNode);

	if (SP_Output && Pelvis_Input) Schema->TryCreateConnection(SP_Output, Pelvis_Input);
	if (Pelvis_Output && Spine_Input) Schema->TryCreateConnection(Pelvis_Output, Spine_Input);
	if (Spine_Output && ResultInputPin) Schema->TryCreateConnection(Spine_Output, ResultInputPin);

	StateGraph->NotifyGraphChanged();
	MarkBlueprintModified(Blueprint, Context);

	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetStringField(TEXT("message"), TEXT("Crouch pose fix applied successfully"));
	return CreateSuccessResponse(Result);
}

bool FAddAnimStateAction::Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError)
{
	if (!ValidateBlueprint(Params, Context, OutError))
	{
		return false;
	}

	FString StateName;
	return GetRequiredString(Params, TEXT("state_name"), StateName, OutError);
}

TSharedPtr<FJsonObject> FAddAnimStateAction::ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context)
{
	UBlueprint* Blueprint = GetTargetBlueprint(Params, Context);
	FString Error;
	FString StateName;
	GetRequiredString(Params, TEXT("state_name"), StateName, Error);

	UAnimBlueprint* AnimBlueprint = ResolveAnimBlueprint(Blueprint, Error);
	if (!AnimBlueprint)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: add_anim_state failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("invalid_blueprint_type"));
	}

	const FString RequestedStateMachineName = GetOptionalString(Params, TEXT("state_machine_name"));
	UAnimationStateMachineGraph* StateMachineGraph = GetStateMachineGraph(AnimBlueprint, RequestedStateMachineName, Error);
	if (!StateMachineGraph)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: add_anim_state failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("state_machine_not_found"));
	}

	if (FindStateNodeByName(StateMachineGraph, StateName))
	{
		return CreateErrorResponse(FString::Printf(TEXT("State '%s' already exists in state machine '%s'"), *StateName, *StateMachineGraph->GetName()), TEXT("duplicate_state"));
	}

	const FVector2D Position = GetNodePositionFromParams(Params);
	UAnimStateNode* NewState = NewObject<UAnimStateNode>(StateMachineGraph);
	if (!NewState)
	{
		return CreateErrorResponse(TEXT("Failed to create animation state node"), TEXT("creation_failed"));
	}

	NewState->CreateNewGuid();
	NewState->NodePosX = static_cast<int32>(Position.X);
	NewState->NodePosY = static_cast<int32>(Position.Y);
	NewState->PostPlacedNewNode();
	NewState->AllocateDefaultPins();
	if (NewState->GetBoundGraph())
	{
		NewState->GetBoundGraph()->Rename(*NormalizeGraphName(StateName), nullptr);
	}
	StateMachineGraph->AddNode(NewState, false, false);
	NewState->SetFlags(RF_Transactional);

	MarkBlueprintModified(Blueprint, Context);
	StateMachineGraph->NotifyGraphChanged();

	UE_LOG(LogMCP, Log, TEXT("UEBridgeEditor: Added anim state '%s' to state machine '%s' in AnimBP '%s'"),
		*StateName, *StateMachineGraph->GetName(), *Blueprint->GetName());

	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetStringField(TEXT("state_machine_name"), StateMachineGraph->GetName());
	Result->SetStringField(TEXT("state_name"), StateName);
	Result->SetStringField(TEXT("state_node_id"), NewState->NodeGuid.ToString());
	Result->SetStringField(TEXT("bound_graph_name"), NewState->GetBoundGraph() ? NewState->GetBoundGraph()->GetName() : TEXT(""));
	return CreateSuccessResponse(Result);
}

bool FAddAnimTransitionAction::Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError)
{
	if (!ValidateBlueprint(Params, Context, OutError))
	{
		return false;
	}

	FString FromState;
	FString ToState;
	if (!GetRequiredString(Params, TEXT("from_state"), FromState, OutError))
	{
		return false;
	}
	return GetRequiredString(Params, TEXT("to_state"), ToState, OutError);
}

TSharedPtr<FJsonObject> FAddAnimTransitionAction::ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context)
{
	UBlueprint* Blueprint = GetTargetBlueprint(Params, Context);
	FString Error;
	FString FromState;
	FString ToState;
	GetRequiredString(Params, TEXT("from_state"), FromState, Error);
	GetRequiredString(Params, TEXT("to_state"), ToState, Error);

	UAnimBlueprint* AnimBlueprint = ResolveAnimBlueprint(Blueprint, Error);
	if (!AnimBlueprint)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: add_anim_transition failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("invalid_blueprint_type"));
	}

	const FString RequestedStateMachineName = GetOptionalString(Params, TEXT("state_machine_name"));
	UAnimationStateMachineGraph* StateMachineGraph = GetStateMachineGraph(AnimBlueprint, RequestedStateMachineName, Error);
	if (!StateMachineGraph)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: add_anim_transition failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("state_machine_not_found"));
	}

	UAnimStateNode* FromStateNode = FindStateNodeByName(StateMachineGraph, FromState);
	if (!FromStateNode)
	{
		return CreateErrorResponse(FString::Printf(TEXT("State '%s' not found in state machine '%s'"), *FromState, *StateMachineGraph->GetName()), TEXT("state_not_found"));
	}

	UAnimStateNode* ToStateNode = FindStateNodeByName(StateMachineGraph, ToState);
	if (!ToStateNode)
	{
		return CreateErrorResponse(FString::Printf(TEXT("State '%s' not found in state machine '%s'"), *ToState, *StateMachineGraph->GetName()), TEXT("state_not_found"));
	}

	if (FindTransitionByEndpoints(StateMachineGraph, GetStateNodeDisplayName(FromStateNode), GetStateNodeDisplayName(ToStateNode)))
	{
		return CreateErrorResponse(FString::Printf(TEXT("Transition '%s' -> '%s' already exists in state machine '%s'"), *FromState, *ToState, *StateMachineGraph->GetName()), TEXT("duplicate_transition"));
	}

	UAnimStateTransitionNode* TransitionNode = NewObject<UAnimStateTransitionNode>(StateMachineGraph);
	if (!TransitionNode)
	{
		return CreateErrorResponse(TEXT("Failed to create transition node"), TEXT("creation_failed"));
	}

	TransitionNode->CreateNewGuid();
	TransitionNode->NodePosX = (FromStateNode->NodePosX + ToStateNode->NodePosX) / 2;
	TransitionNode->NodePosY = (FromStateNode->NodePosY + ToStateNode->NodePosY) / 2;
	TransitionNode->PostPlacedNewNode();
	TransitionNode->AllocateDefaultPins();
	StateMachineGraph->AddNode(TransitionNode, false, false);
	TransitionNode->CreateConnections(FromStateNode, ToStateNode);
	TransitionNode->CrossfadeDuration = static_cast<float>(GetOptionalNumber(Params, TEXT("crossfade_duration"), 0.2));
	TransitionNode->PriorityOrder = static_cast<int32>(GetOptionalNumber(Params, TEXT("priority_order"), 0.0));
	TransitionNode->Bidirectional = false;
	TransitionNode->SetFlags(RF_Transactional);

	MarkBlueprintModified(Blueprint, Context);
	StateMachineGraph->NotifyGraphChanged();

	UE_LOG(LogMCP, Log, TEXT("UEBridgeEditor: Added anim transition '%s' -> '%s' in state machine '%s' for AnimBP '%s'"),
		*FromState, *ToState, *StateMachineGraph->GetName(), *Blueprint->GetName());

	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetStringField(TEXT("state_machine_name"), StateMachineGraph->GetName());
	Result->SetStringField(TEXT("from_state"), FromState);
	Result->SetStringField(TEXT("to_state"), ToState);
	Result->SetStringField(TEXT("transition_node_id"), TransitionNode->NodeGuid.ToString());
	Result->SetStringField(TEXT("rule_graph_name"), TransitionNode->BoundGraph ? TransitionNode->BoundGraph->GetName() : TEXT(""));
	Result->SetNumberField(TEXT("crossfade_duration"), TransitionNode->CrossfadeDuration);
	Result->SetNumberField(TEXT("priority_order"), TransitionNode->PriorityOrder);
	return CreateSuccessResponse(Result);
}

bool FSetAnimTransitionRuleAction::Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError)
{
	if (!ValidateBlueprint(Params, Context, OutError))
	{
		return false;
	}

	FString FromState;
	FString ToState;
	FString BoolVariableName;
	if (!GetRequiredString(Params, TEXT("from_state"), FromState, OutError))
	{
		return false;
	}
	if (!GetRequiredString(Params, TEXT("to_state"), ToState, OutError))
	{
		return false;
	}
	return GetRequiredString(Params, TEXT("bool_variable_name"), BoolVariableName, OutError);
}

TSharedPtr<FJsonObject> FSetAnimTransitionRuleAction::ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context)
{
	UBlueprint* Blueprint = GetTargetBlueprint(Params, Context);
	FString Error;
	FString FromState;
	FString ToState;
	FString BoolVariableName;
	GetRequiredString(Params, TEXT("from_state"), FromState, Error);
	GetRequiredString(Params, TEXT("to_state"), ToState, Error);
	GetRequiredString(Params, TEXT("bool_variable_name"), BoolVariableName, Error);
	const bool bExpectedValue = GetOptionalBool(Params, TEXT("expected_value"), true);

	UAnimBlueprint* AnimBlueprint = ResolveAnimBlueprint(Blueprint, Error);
	if (!AnimBlueprint)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: set_anim_transition_rule failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("invalid_blueprint_type"));
	}

	if (!IsBooleanBlueprintVariable(AnimBlueprint, BoolVariableName))
	{
		return CreateErrorResponse(FString::Printf(TEXT("Boolean variable '%s' was not found in Animation Blueprint '%s' or its parent classes"), *BoolVariableName, *Blueprint->GetName()), TEXT("variable_not_found"));
	}

	const FString RequestedStateMachineName = GetOptionalString(Params, TEXT("state_machine_name"));
	UAnimationStateMachineGraph* StateMachineGraph = GetStateMachineGraph(AnimBlueprint, RequestedStateMachineName, Error);
	if (!StateMachineGraph)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: set_anim_transition_rule failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("state_machine_not_found"));
	}

	UAnimStateTransitionNode* TransitionNode = FindTransitionByEndpoints(StateMachineGraph, FromState, ToState);
	if (!TransitionNode)
	{
		return CreateErrorResponse(FString::Printf(TEXT("Transition '%s' -> '%s' not found in state machine '%s'"), *FromState, *ToState, *StateMachineGraph->GetName()), TEXT("transition_not_found"));
	}

	UEdGraph* RuleGraph = TransitionNode->BoundGraph;
	if (!RuleGraph)
	{
		return CreateErrorResponse(TEXT("Transition rule graph is invalid"), TEXT("rule_graph_invalid"));
	}

	UEdGraphNode* ResultNode = FindTransitionResultNode(RuleGraph);
	if (!ResultNode)
	{
		return CreateErrorResponse(TEXT("Transition result node was not found in rule graph"), TEXT("rule_graph_invalid"));
	}

	ClearRuleGraph(RuleGraph, ResultNode);

	UK2Node_VariableGet* VariableGetNode = FEdGraphSchemaAction_K2NewNode::SpawnNode<UK2Node_VariableGet>(
		RuleGraph,
		FVector2D(-200.0f, 0.0f),
		EK2NewNodeFlags::None,
		[&BoolVariableName](UK2Node_VariableGet* Node)
		{
			Node->VariableReference.SetSelfMember(FName(*BoolVariableName));
		}
	);

	if (!VariableGetNode)
	{
		return CreateErrorResponse(TEXT("Failed to create variable get node in transition rule graph"), TEXT("rule_graph_invalid"));
	}
	VariableGetNode->ReconstructNode();

	UEdGraphPin* BoolOutputPin = nullptr;
	for (UEdGraphPin* Pin : VariableGetNode->Pins)
	{
		if (Pin && Pin->Direction == EGPD_Output && Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Boolean)
		{
			BoolOutputPin = Pin;
			break;
		}
	}

	if (!BoolOutputPin)
	{
		return CreateErrorResponse(TEXT("Failed to resolve boolean output pin for transition rule variable"), TEXT("rule_graph_invalid"));
	}

	if (!bExpectedValue)
	{
		UFunction* NotFunction = UKismetMathLibrary::StaticClass()->FindFunctionByName(TEXT("Not_PreBool"));
		if (!NotFunction)
		{
			return CreateErrorResponse(TEXT("Failed to resolve UKismetMathLibrary::Not_PreBool"), TEXT("rule_graph_invalid"));
		}

		UK2Node_CallFunction* NotNode = FEdGraphSchemaAction_K2NewNode::SpawnNode<UK2Node_CallFunction>(
			RuleGraph,
			FVector2D(-400.0f, 0.0f),
			EK2NewNodeFlags::None,
			[NotFunction](UK2Node_CallFunction* Node)
			{
				Node->SetFromFunction(NotFunction);
			}
		);

		if (!NotNode)
		{
			return CreateErrorResponse(TEXT("Failed to create Not_PreBool node in transition rule graph"), TEXT("rule_graph_invalid"));
		}
		NotNode->ReconstructNode();

		const UEdGraphSchema* Schema = RuleGraph->GetSchema();
		if (!Schema)
		{
			return CreateErrorResponse(TEXT("Transition rule graph has no schema"), TEXT("rule_graph_invalid"));
		}

		UEdGraphPin* NotInputPin = nullptr;
		UEdGraphPin* NotOutputPin = nullptr;
		for (UEdGraphPin* Pin : NotNode->Pins)
		{
			if (!Pin || Pin->PinType.PinCategory != UEdGraphSchema_K2::PC_Boolean)
			{
				continue;
			}

			if (Pin->Direction == EGPD_Input && !NotInputPin)
			{
				NotInputPin = Pin;
			}
			else if (Pin->Direction == EGPD_Output && !NotOutputPin)
			{
				NotOutputPin = Pin;
			}
		}

		if (!NotInputPin || !NotOutputPin || !Schema->TryCreateConnection(BoolOutputPin, NotInputPin))
		{
			return CreateErrorResponse(TEXT("Failed to wire Not_PreBool into transition rule graph"), TEXT("rule_graph_invalid"));
		}

		BoolOutputPin = NotOutputPin;
	}

	UEdGraphPin* CanEnterPin = ResultNode->FindPin(FName(TEXT("bCanEnterTransition")));
	const UEdGraphSchema* Schema = RuleGraph->GetSchema();
	if (!CanEnterPin || !Schema || !Schema->TryCreateConnection(BoolOutputPin, CanEnterPin))
	{
		return CreateErrorResponse(TEXT("Failed to connect transition rule output to result node"), TEXT("rule_graph_invalid"));
	}

	RuleGraph->NotifyGraphChanged();
	MarkBlueprintModified(Blueprint, Context);

	UE_LOG(LogMCP, Log, TEXT("UEBridgeEditor: Set anim transition rule '%s' -> '%s' using bool '%s' == %s in AnimBP '%s'"),
		*FromState, *ToState, *BoolVariableName, bExpectedValue ? TEXT("true") : TEXT("false"), *Blueprint->GetName());

	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetStringField(TEXT("transition_node_id"), TransitionNode->NodeGuid.ToString());
	Result->SetStringField(TEXT("from_state"), FromState);
	Result->SetStringField(TEXT("to_state"), ToState);
	Result->SetStringField(TEXT("bool_variable_name"), BoolVariableName);
	Result->SetBoolField(TEXT("expected_value"), bExpectedValue);
	Result->SetStringField(TEXT("rule_graph_name"), RuleGraph->GetName());
	return CreateSuccessResponse(Result);
}

bool FSetAnimStateAnimationAction::Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError)
{
	if (!ValidateBlueprint(Params, Context, OutError))
	{
		return false;
	}

	FString StateName;
	FString AnimationAsset;
	if (!GetRequiredString(Params, TEXT("state_name"), StateName, OutError))
	{
		return false;
	}
	return GetRequiredString(Params, TEXT("animation_asset"), AnimationAsset, OutError);
}

TSharedPtr<FJsonObject> FSetAnimStateAnimationAction::ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context)
{
	UBlueprint* Blueprint = GetTargetBlueprint(Params, Context);
	FString Error;
	FString StateName;
	FString AnimationAssetPath;
	GetRequiredString(Params, TEXT("state_name"), StateName, Error);
	GetRequiredString(Params, TEXT("animation_asset"), AnimationAssetPath, Error);

	UAnimBlueprint* AnimBlueprint = ResolveAnimBlueprint(Blueprint, Error);
	if (!AnimBlueprint)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: set_anim_state_animation failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("invalid_blueprint_type"));
	}

	const FString RequestedStateMachineName = GetOptionalString(Params, TEXT("state_machine_name"));
	UAnimationStateMachineGraph* StateMachineGraph = GetStateMachineGraph(AnimBlueprint, RequestedStateMachineName, Error);
	if (!StateMachineGraph)
	{
		UE_LOG(LogMCP, Warning, TEXT("UEBridgeEditor: set_anim_state_animation failed: %s"), *Error);
		return CreateErrorResponse(Error, TEXT("state_machine_not_found"));
	}

	UAnimStateNode* StateNode = FindStateNodeByName(StateMachineGraph, StateName);
	if (!StateNode)
	{
		return CreateErrorResponse(FString::Printf(TEXT("State '%s' not found in state machine '%s'"), *StateName, *StateMachineGraph->GetName()), TEXT("state_not_found"));
	}

	UEdGraph* StateGraph = StateNode->GetBoundGraph();
	if (!StateGraph)
	{
		return CreateErrorResponse(TEXT("State graph is invalid"), TEXT("state_graph_invalid"));
	}

	UAnimSequence* AnimSequence = Cast<UAnimSequence>(UEditorAssetLibrary::LoadAsset(AnimationAssetPath));
	if (!AnimSequence)
	{
		return CreateErrorResponse(FString::Printf(TEXT("Animation asset '%s' could not be loaded as UAnimSequence"), *AnimationAssetPath), TEXT("invalid_animation_asset"));
	}

	UEdGraphNode* ResultNode = FindStateResultNode(StateGraph);
	if (!ResultNode)
	{
		return CreateErrorResponse(TEXT("State result node was not found in state graph"), TEXT("state_graph_invalid"));
	}

	ClearStateGraph(StateGraph, ResultNode);

	UAnimGraphNode_SequencePlayer* SequencePlayerNode = NewObject<UAnimGraphNode_SequencePlayer>(StateGraph);
	if (!SequencePlayerNode)
	{
		return CreateErrorResponse(TEXT("Failed to create sequence player node"), TEXT("state_graph_invalid"));
	}

	SequencePlayerNode->CreateNewGuid();
	SequencePlayerNode->PostPlacedNewNode();
	SequencePlayerNode->AllocateDefaultPins();
	SequencePlayerNode->NodePosX = 0;
	SequencePlayerNode->NodePosY = 0;
	StateGraph->AddNode(SequencePlayerNode, false, false);
	SequencePlayerNode->SetAnimationAsset(AnimSequence);
	SequencePlayerNode->SetFlags(RF_Transactional);

	UEdGraphPin* PoseOutputPin = FindFirstOutputPin(SequencePlayerNode);
	UEdGraphPin* ResultInputPin = FindFirstInputPin(ResultNode);
	const UEdGraphSchema* Schema = StateGraph->GetSchema();
	if (!PoseOutputPin || !ResultInputPin || !Schema || !Schema->TryCreateConnection(PoseOutputPin, ResultInputPin))
	{
		return CreateErrorResponse(TEXT("Failed to connect sequence player to state result node"), TEXT("state_graph_invalid"));
	}

	StateGraph->NotifyGraphChanged();
	MarkBlueprintModified(Blueprint, Context);

	UE_LOG(LogMCP, Log, TEXT("UEBridgeEditor: Set animation state '%s' to sequence '%s' in AnimBP '%s'"),
		*StateName, *AnimationAssetPath, *Blueprint->GetName());

	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetStringField(TEXT("state_name"), StateName);
	Result->SetStringField(TEXT("state_node_id"), StateNode->NodeGuid.ToString());
	Result->SetStringField(TEXT("bound_graph_name"), StateGraph->GetName());
	Result->SetStringField(TEXT("animation_asset"), AnimationAssetPath);
	return CreateSuccessResponse(Result);
}
