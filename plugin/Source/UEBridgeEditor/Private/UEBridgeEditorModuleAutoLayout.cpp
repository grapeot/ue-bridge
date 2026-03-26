#include "UEBridgeEditorModuleAutoLayout.h"

#include "BlueprintAutoLayoutCommands.h"
#include "Actions/LayoutActions.h"
#include "BlueprintEditor.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "ScopedTransaction.h"
#include "UEBridgeCommonUtils.h"

#define LOCTEXT_NAMESPACE "FUEBridgeEditorModuleAutoLayout"

void UEBridgeEditorModuleAutoLayout::ExecuteAutoLayoutSmart()
{
	FBlueprintEditor* BPEditor = FUEBridgeCommonUtils::GetActiveBlueprintEditor();
	if (!BPEditor)
	{
		UE_LOG(LogMCP, Warning, TEXT("AutoLayout: No focused Blueprint editor."));
		return;
	}

	UEdGraph* Graph = BPEditor->GetFocusedGraph();
	if (!Graph)
	{
		return;
	}

	FGraphPanelSelectionSet SelectedNodes = BPEditor->GetSelectedNodes();
	TArray<UEdGraphNode*> NodesToLayout;
	for (UObject* Obj : SelectedNodes)
	{
		UEdGraphNode* Node = Cast<UEdGraphNode>(Obj);
		if (Node && Graph->Nodes.Contains(Node))
		{
			NodesToLayout.Add(Node);
		}
	}

	FBlueprintLayoutSettings Settings;

	if (NodesToLayout.Num() > 0)
	{
		// Auto-expand: include pure dependencies of selected nodes
		TSet<UEdGraphNode*> LayoutSet;
		for (UEdGraphNode* N : NodesToLayout) { if (N) LayoutSet.Add(N); }

		{
			TSet<UEdGraphNode*> GraphNodeSet;
			for (UEdGraphNode* GN : Graph->Nodes) { if (GN) GraphNodeSet.Add(GN); }
			TSet<UEdGraphNode*> PureVisited;
			TArray<UEdGraphNode*> ExtraPures;
			for (UEdGraphNode* N : TArray<UEdGraphNode*>(NodesToLayout))
			{
				if (!N) continue;
				FBlueprintAutoLayout::CollectPureDependencies(N, GraphNodeSet, ExtraPures, PureVisited, 5);
			}
			for (UEdGraphNode* Pure : ExtraPures)
			{
				if (Pure && !LayoutSet.Contains(Pure))
				{
					NodesToLayout.Add(Pure);
					LayoutSet.Add(Pure);
				}
			}
		}

		// Collect surrounding nodes for avoidance (all non-selected graph nodes)
		TArray<UEdGraphNode*> SurroundingNodes;
		for (UEdGraphNode* N : Graph->Nodes)
		{
			if (N && !LayoutSet.Contains(N))
			{
				SurroundingNodes.Add(N);
			}
		}

		Settings.bAvoidSurrounding = true;
		const TArray<UEdGraphNode*>* SurrPtr = SurroundingNodes.Num() > 0 ? &SurroundingNodes : nullptr;

		FScopedTransaction Transaction(LOCTEXT("AutoLayoutSmartSelected", "Auto Layout Selected"));
		int32 Moved = FBlueprintAutoLayout::LayoutNodes(Graph, NodesToLayout, Settings, SurrPtr);
		UE_LOG(LogMCP, Log, TEXT("AutoLayout: selected mode, %d nodes (incl. pure deps) moved"), Moved);
		return;
	}

	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (Node)
		{
			NodesToLayout.Add(Node);
		}
	}

	if (NodesToLayout.Num() == 0)
	{
		return;
	}

	FScopedTransaction Transaction(LOCTEXT("AutoLayoutSmartGraph", "Auto Layout Graph"));
	int32 Moved = FBlueprintAutoLayout::LayoutNodes(Graph, NodesToLayout, Settings);
	UE_LOG(LogMCP, Log, TEXT("AutoLayout: graph mode, %d/%d nodes moved"), Moved, NodesToLayout.Num());
}

void UEBridgeEditorModuleAutoLayout::ExecuteAutoLayoutSelected()
{
	FBlueprintEditor* BPEditor = FUEBridgeCommonUtils::GetActiveBlueprintEditor();
	if (!BPEditor)
	{
		UE_LOG(LogMCP, Warning, TEXT("AutoLayout: No focused Blueprint editor."));
		return;
	}

	UEdGraph* Graph = BPEditor->GetFocusedGraph();
	if (!Graph) return;

	FGraphPanelSelectionSet SelectedNodes = BPEditor->GetSelectedNodes();
	TArray<UEdGraphNode*> NodesToLayout;
	for (UObject* Obj : SelectedNodes)
	{
		UEdGraphNode* Node = Cast<UEdGraphNode>(Obj);
		if (Node && Graph->Nodes.Contains(Node))
		{
			NodesToLayout.Add(Node);
		}
	}

	if (NodesToLayout.Num() == 0)
	{
		UE_LOG(LogMCP, Warning, TEXT("AutoLayout Selected: No nodes selected."));
		return;
	}

	FScopedTransaction Transaction(LOCTEXT("AutoLayoutSelected", "Auto Layout Selected"));
	int32 Moved = FBlueprintAutoLayout::LayoutNodes(Graph, NodesToLayout);
	UE_LOG(LogMCP, Log, TEXT("AutoLayout Selected: %d nodes moved"), Moved);
}


void UEBridgeEditorModuleAutoLayout::ExecuteAutoLayoutSubtree()
{
	FBlueprintEditor* BPEditor = FUEBridgeCommonUtils::GetActiveBlueprintEditor();
	if (!BPEditor)
	{
		UE_LOG(LogMCP, Warning, TEXT("AutoLayout: No focused Blueprint editor."));
		return;
	}

	UEdGraph* Graph = BPEditor->GetFocusedGraph();
	if (!Graph) return;

	UEdGraphNode* Root = BPEditor->GetSingleSelectedNode();
	if (!Root)
	{
		UE_LOG(LogMCP, Warning, TEXT("AutoLayout Subtree: Select a single root node."));
		return;
	}

	TArray<UEdGraphNode*> Subtree = FBlueprintAutoLayout::CollectExecSubtree(Root, 3);
	if (Subtree.Num() == 0) return;

	FScopedTransaction Transaction(LOCTEXT("AutoLayoutSubtree", "Auto Layout Subtree"));
	int32 Moved = FBlueprintAutoLayout::LayoutNodes(Graph, Subtree);
	UE_LOG(LogMCP, Log, TEXT("AutoLayout Subtree: %d/%d nodes moved"), Moved, Subtree.Num());
}


void UEBridgeEditorModuleAutoLayout::ExecuteAutoLayoutGraph()
{
	FBlueprintEditor* BPEditor = FUEBridgeCommonUtils::GetActiveBlueprintEditor();
	if (!BPEditor)
	{
		UE_LOG(LogMCP, Warning, TEXT("AutoLayout: No focused Blueprint editor."));
		return;
	}

	UEdGraph* Graph = BPEditor->GetFocusedGraph();
	if (!Graph) return;

	TArray<UEdGraphNode*> AllNodes;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (Node) AllNodes.Add(Node);
	}

	if (AllNodes.Num() == 0) return;

	FScopedTransaction Transaction(LOCTEXT("AutoLayoutGraph", "Auto Layout Graph"));
	int32 Moved = FBlueprintAutoLayout::LayoutNodes(Graph, AllNodes);
	UE_LOG(LogMCP, Log, TEXT("AutoLayout Graph: %d/%d nodes moved"), Moved, AllNodes.Num());
}



#undef LOCTEXT_NAMESPACE
