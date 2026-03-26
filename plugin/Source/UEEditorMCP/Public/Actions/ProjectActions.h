// Copyright (c) 2025 zolnoor. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "Actions/EditorAction.h"

/**
 * Create legacy input mapping (Action or Axis)
 */
class UEEDITORMCP_API FCreateInputMappingAction : public FEditorAction
{
public:
	virtual FString GetActionName() const override { return TEXT("CreateInputMapping"); }

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;
};

/**
 * Create Enhanced Input Action asset
 */
class UEEDITORMCP_API FCreateInputActionAction : public FEditorAction
{
public:
	virtual FString GetActionName() const override { return TEXT("CreateInputAction"); }

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;
};

/**
 * Create Enhanced Input Mapping Context asset
 */
class UEEDITORMCP_API FCreateInputMappingContextAction : public FEditorAction
{
public:
	virtual FString GetActionName() const override { return TEXT("CreateInputMappingContext"); }

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;
};

/**
 * Add key mapping to Input Mapping Context with optional modifiers
 */
class UEEDITORMCP_API FAddKeyMappingToContextAction : public FEditorAction
{
public:
	virtual FString GetActionName() const override { return TEXT("AddKeyMappingToContext"); }

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;
};

/**
 * Read all mappings from an Input Mapping Context
 */
class UEEDITORMCP_API FReadIMCAction : public FEditorAction
{
public:
	virtual FString GetActionName() const override { return TEXT("ReadIMC"); }

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;
};

/**
 * Remove key mapping(s) from an Input Mapping Context
 */
class UEEDITORMCP_API FRemoveKeyMappingFromContextAction : public FEditorAction
{
public:
	virtual FString GetActionName() const override { return TEXT("RemoveKeyMappingFromContext"); }

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;
};
