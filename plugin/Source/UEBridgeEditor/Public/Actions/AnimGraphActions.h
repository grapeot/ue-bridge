// Copyright (c) 2026 Yan Wang. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "Actions/EditorAction.h"

class UAnimBlueprint;
class UAnimationStateMachineGraph;
class UAnimStateNode;
class UAnimStateTransitionNode;
class UEdGraph;

class UEBRIDGEEDITOR_API FListAnimStatesAction : public FBlueprintAction
{
public:
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual FString GetActionName() const override { return TEXT("list_anim_states"); }
};

class UEBRIDGEEDITOR_API FAddAnimStateAction : public FBlueprintAction
{
public:
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual FString GetActionName() const override { return TEXT("add_anim_state"); }
};

class UEBRIDGEEDITOR_API FAddAnimTransitionAction : public FBlueprintAction
{
public:
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual FString GetActionName() const override { return TEXT("add_anim_transition"); }
};

class UEBRIDGEEDITOR_API FSetAnimTransitionRuleAction : public FBlueprintAction
{
public:
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual FString GetActionName() const override { return TEXT("set_anim_transition_rule"); }
};

class UEBRIDGEEDITOR_API FSetAnimStateAnimationAction : public FBlueprintAction
{
public:
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual FString GetActionName() const override { return TEXT("set_anim_state_animation"); }
};

class UEBRIDGEEDITOR_API FApplyCrouchPoseFixAction : public FBlueprintAction
{
public:
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual FString GetActionName() const override { return TEXT("apply_crouch_pose_fix"); }
};
