#include "ActionRegistry.h"

#include "Actions/BlueprintActions.h"
#include "Actions/EditorAction.h"
#include "Actions/EditorActions.h"
#include "Actions/NodeActions.h"
#include "Actions/GraphActions.h"
#include "Actions/ProjectActions.h"
#include "Actions/UMGActions.h"
#include "Actions/MaterialActions.h"
#include "Actions/LayoutActions.h"
#include "Actions/EditorDiffActions.h"

namespace
{
void RegisterBlueprintActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
	ActionHandlers.Add(TEXT("create_blueprint"), MakeShared<FCreateBlueprintAction>());
	ActionHandlers.Add(TEXT("compile_blueprint"), MakeShared<FCompileBlueprintAction>());
	ActionHandlers.Add(TEXT("add_component_to_blueprint"), MakeShared<FAddComponentToBlueprintAction>());
	ActionHandlers.Add(TEXT("spawn_blueprint_actor"), MakeShared<FSpawnBlueprintActorAction>());
	ActionHandlers.Add(TEXT("set_component_property"), MakeShared<FSetComponentPropertyAction>());
	ActionHandlers.Add(TEXT("set_inherited_component_property"), MakeShared<FSetInheritedComponentPropertyAction>());
	ActionHandlers.Add(TEXT("set_static_mesh_properties"), MakeShared<FSetStaticMeshPropertiesAction>());
	ActionHandlers.Add(TEXT("set_physics_properties"), MakeShared<FSetPhysicsPropertiesAction>());
	ActionHandlers.Add(TEXT("set_blueprint_property"), MakeShared<FSetBlueprintPropertyAction>());
	ActionHandlers.Add(TEXT("create_colored_material"), MakeShared<FCreateColoredMaterialAction>());
	ActionHandlers.Add(TEXT("set_blueprint_parent_class"), MakeShared<FSetBlueprintParentClassAction>());
	ActionHandlers.Add(TEXT("add_blueprint_interface"), MakeShared<FAddBlueprintInterfaceAction>());
	ActionHandlers.Add(TEXT("remove_blueprint_interface"), MakeShared<FRemoveBlueprintInterfaceAction>());
}

void RegisterEditorActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
	ActionHandlers.Add(TEXT("get_actors_in_level"), MakeShared<FGetActorsInLevelAction>());
	ActionHandlers.Add(TEXT("find_actors_by_name"), MakeShared<FFindActorsByNameAction>());
	ActionHandlers.Add(TEXT("spawn_actor"), MakeShared<FSpawnActorAction>());
	ActionHandlers.Add(TEXT("delete_actor"), MakeShared<FDeleteActorAction>());
	ActionHandlers.Add(TEXT("set_actor_transform"), MakeShared<FSetActorTransformAction>());
	ActionHandlers.Add(TEXT("get_actor_properties"), MakeShared<FGetActorPropertiesAction>());
	ActionHandlers.Add(TEXT("set_actor_property"), MakeShared<FSetActorPropertyAction>());
	ActionHandlers.Add(TEXT("focus_viewport"), MakeShared<FFocusViewportAction>());
	ActionHandlers.Add(TEXT("get_viewport_transform"), MakeShared<FGetViewportTransformAction>());
	ActionHandlers.Add(TEXT("set_viewport_transform"), MakeShared<FSetViewportTransformAction>());
	ActionHandlers.Add(TEXT("save_all"), MakeShared<FSaveAllAction>());
	ActionHandlers.Add(TEXT("list_assets"), MakeShared<FListAssetsAction>());
	ActionHandlers.Add(TEXT("rename_assets"), MakeShared<FRenameAssetsAction>());
	ActionHandlers.Add(TEXT("get_selected_asset_thumbnail"), MakeShared<FGetSelectedAssetThumbnailAction>());
	ActionHandlers.Add(TEXT("get_selected_assets"), MakeShared<FGetSelectedAssetsAction>());
	ActionHandlers.Add(TEXT("get_blueprint_summary"), MakeShared<FGetBlueprintSummaryAction>());
	ActionHandlers.Add(TEXT("describe_blueprint_full"), MakeShared<FDescribeFullAction>());
	ActionHandlers.Add(TEXT("get_editor_logs"), MakeShared<FGetEditorLogsAction>());
	ActionHandlers.Add(TEXT("get_unreal_logs"), MakeShared<FGetUnrealLogsAction>());
	ActionHandlers.Add(TEXT("batch_execute"), MakeShared<FBatchExecuteAction>());
	ActionHandlers.Add(TEXT("is_ready"), MakeShared<FEditorIsReadyAction>());
	ActionHandlers.Add(TEXT("request_shutdown"), MakeShared<FRequestEditorShutdownAction>());
	ActionHandlers.Add(TEXT("start_pie"), MakeShared<FStartPIEAction>());
	ActionHandlers.Add(TEXT("stop_pie"), MakeShared<FStopPIEAction>());
	ActionHandlers.Add(TEXT("get_pie_state"), MakeShared<FGetPIEStateAction>());
	ActionHandlers.Add(TEXT("clear_logs"), MakeShared<FClearLogsAction>());
	ActionHandlers.Add(TEXT("assert_log"), MakeShared<FAssertLogAction>());
	ActionHandlers.Add(TEXT("rename_actor_label"), MakeShared<FRenameActorLabelAction>());
	ActionHandlers.Add(TEXT("set_actor_folder"), MakeShared<FSetActorFolderAction>());
	ActionHandlers.Add(TEXT("select_actors"), MakeShared<FSelectActorsAction>());
	ActionHandlers.Add(TEXT("get_outliner_tree"), MakeShared<FGetOutlinerTreeAction>());
	ActionHandlers.Add(TEXT("open_asset_editor"), MakeShared<FOpenAssetEditorAction>());
	ActionHandlers.Add(TEXT("new_level"), MakeShared<FNewLevelAction>());
	ActionHandlers.Add(TEXT("take_screenshot"), MakeShared<FTakeScreenshotAction>());
}

void RegisterLayoutActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
	ActionHandlers.Add(TEXT("auto_layout_selected"), MakeShared<FAutoLayoutSelectedAction>());
	ActionHandlers.Add(TEXT("auto_layout_subtree"), MakeShared<FAutoLayoutSubtreeAction>());
	ActionHandlers.Add(TEXT("auto_layout_blueprint"), MakeShared<FAutoLayoutBlueprintAction>());
	ActionHandlers.Add(TEXT("layout_and_comment"), MakeShared<FLayoutAndCommentAction>());
}

void RegisterNodeActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
	ActionHandlers.Add(TEXT("connect_blueprint_nodes"), MakeShared<FConnectBlueprintNodesAction>());
	ActionHandlers.Add(TEXT("find_blueprint_nodes"), MakeShared<FFindBlueprintNodesAction>());
	ActionHandlers.Add(TEXT("delete_blueprint_node"), MakeShared<FDeleteBlueprintNodeAction>());
	ActionHandlers.Add(TEXT("get_node_pins"), MakeShared<FGetNodePinsAction>());
	ActionHandlers.Add(TEXT("describe_graph"), MakeShared<FDescribeGraphAction>());
	ActionHandlers.Add(TEXT("get_selected_nodes"), MakeShared<FGetSelectedNodesAction>());
	ActionHandlers.Add(TEXT("collapse_selection_to_function"), MakeShared<FCollapseSelectionToFunctionAction>());
	ActionHandlers.Add(TEXT("collapse_selection_to_macro"), MakeShared<FCollapseSelectionToMacroAction>());
	ActionHandlers.Add(TEXT("set_selected_nodes"), MakeShared<FSetSelectedNodesAction>());
	ActionHandlers.Add(TEXT("batch_select_and_act"), MakeShared<FBatchSelectAndActAction>());
	ActionHandlers.Add(TEXT("add_blueprint_event_node"), MakeShared<FAddBlueprintEventNodeAction>());
	ActionHandlers.Add(TEXT("add_blueprint_input_action_node"), MakeShared<FAddBlueprintInputActionNodeAction>());
	ActionHandlers.Add(TEXT("add_enhanced_input_action_node"), MakeShared<FAddEnhancedInputActionNodeAction>());
	ActionHandlers.Add(TEXT("add_blueprint_custom_event"), MakeShared<FAddBlueprintCustomEventAction>());
	ActionHandlers.Add(TEXT("add_custom_event_for_delegate"), MakeShared<FAddCustomEventForDelegateAction>());
	ActionHandlers.Add(TEXT("add_blueprint_variable"), MakeShared<FAddBlueprintVariableAction>());
	ActionHandlers.Add(TEXT("add_blueprint_variable_get"), MakeShared<FAddBlueprintVariableGetAction>());
	ActionHandlers.Add(TEXT("add_blueprint_variable_set"), MakeShared<FAddBlueprintVariableSetAction>());
	ActionHandlers.Add(TEXT("set_node_pin_default"), MakeShared<FSetNodePinDefaultAction>());
	ActionHandlers.Add(TEXT("add_blueprint_function_node"), MakeShared<FAddBlueprintFunctionNodeAction>());
	ActionHandlers.Add(TEXT("add_blueprint_self_reference"), MakeShared<FAddBlueprintSelfReferenceAction>());
	ActionHandlers.Add(TEXT("add_blueprint_get_self_component_reference"), MakeShared<FAddBlueprintGetSelfComponentReferenceAction>());
	ActionHandlers.Add(TEXT("add_blueprint_branch_node"), MakeShared<FAddBlueprintBranchNodeAction>());
	ActionHandlers.Add(TEXT("add_blueprint_cast_node"), MakeShared<FAddBlueprintCastNodeAction>());
	ActionHandlers.Add(TEXT("add_blueprint_get_subsystem_node"), MakeShared<FAddBlueprintGetSubsystemNodeAction>());
	ActionHandlers.Add(TEXT("create_blueprint_function"), MakeShared<FCreateBlueprintFunctionAction>());
	ActionHandlers.Add(TEXT("add_event_dispatcher"), MakeShared<FAddEventDispatcherAction>());
	ActionHandlers.Add(TEXT("call_event_dispatcher"), MakeShared<FCallEventDispatcherAction>());
	ActionHandlers.Add(TEXT("bind_event_dispatcher"), MakeShared<FBindEventDispatcherAction>());
	ActionHandlers.Add(TEXT("create_event_delegate"), MakeShared<FCreateEventDelegateAction>());
	ActionHandlers.Add(TEXT("bind_component_event"), MakeShared<FBindComponentEventAction>());
	ActionHandlers.Add(TEXT("add_spawn_actor_from_class_node"), MakeShared<FAddSpawnActorFromClassNodeAction>());
	ActionHandlers.Add(TEXT("call_blueprint_function"), MakeShared<FCallBlueprintFunctionAction>());
	ActionHandlers.Add(TEXT("set_object_property"), MakeShared<FSetObjectPropertyAction>());
	ActionHandlers.Add(TEXT("add_sequence_node"), MakeShared<FAddSequenceNodeAction>());
	ActionHandlers.Add(TEXT("add_macro_instance_node"), MakeShared<FAddMacroInstanceNodeAction>());
	ActionHandlers.Add(TEXT("add_make_struct_node"), MakeShared<FAddMakeStructNodeAction>());
	ActionHandlers.Add(TEXT("add_break_struct_node"), MakeShared<FAddBreakStructNodeAction>());
	ActionHandlers.Add(TEXT("add_switch_on_string_node"), MakeShared<FAddSwitchOnStringNodeAction>());
	ActionHandlers.Add(TEXT("add_switch_on_int_node"), MakeShared<FAddSwitchOnIntNodeAction>());
	ActionHandlers.Add(TEXT("add_function_local_variable"), MakeShared<FAddFunctionLocalVariableAction>());
	ActionHandlers.Add(TEXT("set_blueprint_variable_default"), MakeShared<FSetBlueprintVariableDefaultAction>());
	ActionHandlers.Add(TEXT("add_blueprint_comment"), MakeShared<FAddBlueprintCommentAction>());
	ActionHandlers.Add(TEXT("auto_comment"), MakeShared<FAutoCommentAction>());
	ActionHandlers.Add(TEXT("delete_blueprint_variable"), MakeShared<FDeleteBlueprintVariableAction>());
	ActionHandlers.Add(TEXT("rename_blueprint_variable"), MakeShared<FRenameBlueprintVariableAction>());
	ActionHandlers.Add(TEXT("set_variable_metadata"), MakeShared<FSetVariableMetadataAction>());
	ActionHandlers.Add(TEXT("delete_blueprint_function"), MakeShared<FDeleteBlueprintFunctionAction>());
	ActionHandlers.Add(TEXT("rename_blueprint_function"), MakeShared<FRenameBlueprintFunctionAction>());
	ActionHandlers.Add(TEXT("rename_blueprint_macro"), MakeShared<FRenameBlueprintMacroAction>());
	ActionHandlers.Add(TEXT("disconnect_blueprint_pin"), MakeShared<FDisconnectBlueprintPinAction>());
	ActionHandlers.Add(TEXT("move_node"), MakeShared<FMoveNodeAction>());
	ActionHandlers.Add(TEXT("add_reroute_node"), MakeShared<FAddRerouteNodeAction>());
	ActionHandlers.Add(TEXT("describe_graph_enhanced"), MakeShared<FGraphDescribeEnhancedAction>());
	ActionHandlers.Add(TEXT("apply_graph_patch"), MakeShared<FApplyPatchAction>());
	ActionHandlers.Add(TEXT("validate_graph_patch"), MakeShared<FValidatePatchAction>());
	ActionHandlers.Add(TEXT("export_nodes_to_text"), MakeShared<FExportNodesToTextAction>());
	ActionHandlers.Add(TEXT("import_nodes_from_text"), MakeShared<FImportNodesFromTextAction>());
}

void RegisterProjectActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
	ActionHandlers.Add(TEXT("create_input_mapping"), MakeShared<FCreateInputMappingAction>());
	ActionHandlers.Add(TEXT("create_input_action"), MakeShared<FCreateInputActionAction>());
	ActionHandlers.Add(TEXT("create_input_mapping_context"), MakeShared<FCreateInputMappingContextAction>());
	ActionHandlers.Add(TEXT("add_key_mapping_to_context"), MakeShared<FAddKeyMappingToContextAction>());
	ActionHandlers.Add(TEXT("read_imc"), MakeShared<FReadIMCAction>());
	ActionHandlers.Add(TEXT("remove_key_mapping_from_context"), MakeShared<FRemoveKeyMappingFromContextAction>());
}

void RegisterUMGActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
	ActionHandlers.Add(TEXT("create_umg_widget_blueprint"), MakeShared<FCreateUMGWidgetBlueprintAction>());
	ActionHandlers.Add(TEXT("add_text_block_to_widget"), MakeShared<FAddTextBlockToWidgetAction>());
	ActionHandlers.Add(TEXT("add_button_to_widget"), MakeShared<FAddButtonToWidgetAction>());
	ActionHandlers.Add(TEXT("add_image_to_widget"), MakeShared<FAddImageToWidgetAction>());
	ActionHandlers.Add(TEXT("add_border_to_widget"), MakeShared<FAddBorderToWidgetAction>());
	ActionHandlers.Add(TEXT("add_overlay_to_widget"), MakeShared<FAddOverlayToWidgetAction>());
	ActionHandlers.Add(TEXT("add_horizontal_box_to_widget"), MakeShared<FAddHorizontalBoxToWidgetAction>());
	ActionHandlers.Add(TEXT("add_vertical_box_to_widget"), MakeShared<FAddVerticalBoxToWidgetAction>());
	ActionHandlers.Add(TEXT("add_slider_to_widget"), MakeShared<FAddSliderToWidgetAction>());
	ActionHandlers.Add(TEXT("add_progress_bar_to_widget"), MakeShared<FAddProgressBarToWidgetAction>());
	ActionHandlers.Add(TEXT("add_size_box_to_widget"), MakeShared<FAddSizeBoxToWidgetAction>());
	ActionHandlers.Add(TEXT("add_scale_box_to_widget"), MakeShared<FAddScaleBoxToWidgetAction>());
	ActionHandlers.Add(TEXT("add_canvas_panel_to_widget"), MakeShared<FAddCanvasPanelToWidgetAction>());
	ActionHandlers.Add(TEXT("add_combo_box_to_widget"), MakeShared<FAddComboBoxToWidgetAction>());
	ActionHandlers.Add(TEXT("add_check_box_to_widget"), MakeShared<FAddCheckBoxToWidgetAction>());
	ActionHandlers.Add(TEXT("add_spin_box_to_widget"), MakeShared<FAddSpinBoxToWidgetAction>());
	ActionHandlers.Add(TEXT("add_editable_text_box_to_widget"), MakeShared<FAddEditableTextBoxToWidgetAction>());
	ActionHandlers.Add(TEXT("bind_widget_event"), MakeShared<FBindWidgetEventAction>());
	ActionHandlers.Add(TEXT("add_widget_to_viewport"), MakeShared<FAddWidgetToViewportAction>());
	ActionHandlers.Add(TEXT("set_text_block_binding"), MakeShared<FSetTextBlockBindingAction>());
	ActionHandlers.Add(TEXT("list_widget_components"), MakeShared<FListWidgetComponentsAction>());
	ActionHandlers.Add(TEXT("reparent_widgets"), MakeShared<FReparentWidgetsAction>());
	ActionHandlers.Add(TEXT("set_widget_properties"), MakeShared<FSetWidgetPropertiesAction>());
	ActionHandlers.Add(TEXT("get_widget_tree"), MakeShared<FGetWidgetTreeAction>());
	ActionHandlers.Add(TEXT("delete_widget_from_blueprint"), MakeShared<FDeleteWidgetFromBlueprintAction>());
	ActionHandlers.Add(TEXT("rename_widget_in_blueprint"), MakeShared<FRenameWidgetInBlueprintAction>());
	ActionHandlers.Add(TEXT("add_widget_child"), MakeShared<FAddWidgetChildAction>());
	ActionHandlers.Add(TEXT("delete_umg_widget_blueprint"), MakeShared<FDeleteUMGWidgetBlueprintAction>());
	ActionHandlers.Add(TEXT("set_combo_box_options"), MakeShared<FSetComboBoxOptionsAction>());
	ActionHandlers.Add(TEXT("set_widget_text"), MakeShared<FSetWidgetTextAction>());
	ActionHandlers.Add(TEXT("set_slider_properties"), MakeShared<FSetSliderPropertiesAction>());
	ActionHandlers.Add(TEXT("add_generic_widget_to_widget"), MakeShared<FAddGenericWidgetAction>());
	ActionHandlers.Add(TEXT("mvvm_add_viewmodel"), MakeShared<FMVVMAddViewModelAction>());
	ActionHandlers.Add(TEXT("mvvm_add_binding"), MakeShared<FMVVMAddBindingAction>());
	ActionHandlers.Add(TEXT("mvvm_get_bindings"), MakeShared<FMVVMGetBindingsAction>());
	ActionHandlers.Add(TEXT("mvvm_remove_binding"), MakeShared<FMVVMRemoveBindingAction>());
	ActionHandlers.Add(TEXT("mvvm_remove_viewmodel"), MakeShared<FMVVMRemoveViewModelAction>());
}

void RegisterMaterialActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
	ActionHandlers.Add(TEXT("create_material"), MakeShared<FCreateMaterialAction>());
	ActionHandlers.Add(TEXT("set_material_property"), MakeShared<FSetMaterialPropertyAction>());
	ActionHandlers.Add(TEXT("add_material_expression"), MakeShared<FAddMaterialExpressionAction>());
	ActionHandlers.Add(TEXT("connect_material_expressions"), MakeShared<FConnectMaterialExpressionsAction>());
	ActionHandlers.Add(TEXT("connect_to_material_output"), MakeShared<FConnectToMaterialOutputAction>());
	ActionHandlers.Add(TEXT("set_material_expression_property"), MakeShared<FSetMaterialExpressionPropertyAction>());
	ActionHandlers.Add(TEXT("compile_material"), MakeShared<FCompileMaterialAction>());
	ActionHandlers.Add(TEXT("create_material_instance"), MakeShared<FCreateMaterialInstanceAction>());
	ActionHandlers.Add(TEXT("create_post_process_volume"), MakeShared<FCreatePostProcessVolumeAction>());
	ActionHandlers.Add(TEXT("get_material_summary"), MakeShared<FGetMaterialSummaryAction>());
	ActionHandlers.Add(TEXT("remove_material_expression"), MakeShared<FRemoveMaterialExpressionAction>());
	ActionHandlers.Add(TEXT("auto_layout_material"), MakeShared<FAutoLayoutMaterialAction>());
	ActionHandlers.Add(TEXT("auto_comment_material"), MakeShared<FAutoCommentMaterialAction>());
	ActionHandlers.Add(TEXT("get_material_selected_nodes"), MakeShared<FGetMaterialSelectedNodesAction>());
	ActionHandlers.Add(TEXT("apply_material_to_component"), MakeShared<FApplyMaterialToComponentAction>());
	ActionHandlers.Add(TEXT("apply_material_to_actor"), MakeShared<FApplyMaterialToActorAction>());
	ActionHandlers.Add(TEXT("refresh_material_editor"), MakeShared<FRefreshMaterialEditorAction>());
}

void RegisterDiffActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
	ActionHandlers.Add(TEXT("diff_against_depot"), MakeShared<FDiffAgainstDepotAction>());
	ActionHandlers.Add(TEXT("get_asset_history"), MakeShared<FGetAssetHistoryAction>());
}
}

void FUEEditorActionRegistry::RegisterDefaultActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
	RegisterBlueprintActions(ActionHandlers);
	RegisterEditorActions(ActionHandlers);
	RegisterLayoutActions(ActionHandlers);
	RegisterNodeActions(ActionHandlers);
	RegisterProjectActions(ActionHandlers);
	RegisterUMGActions(ActionHandlers);
	RegisterMaterialActions(ActionHandlers);
	RegisterDiffActions(ActionHandlers);
}
