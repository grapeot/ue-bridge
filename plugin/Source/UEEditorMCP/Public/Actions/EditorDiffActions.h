// Copyright (c) 2025 zolnoor. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "EditorAction.h"

/**
 * FDiffAgainstDepotAction
 *
 * Programmatic "Diff Against Depot" — compares a local asset against
 * the latest source-control revision and returns structured diff data
 * as JSON (no UI).
 *
 * For Blueprints the diff walks every graph and produces per-node
 * results (added / removed / modified / moved …).
 * For generic assets it falls back to object-property comparison.
 *
 * Params:
 *   asset_path  (string, required)  — e.g. "/Game/P110_2/Blueprints/BP_Foo"
 *   revision    (int, optional)     — specific revision number (default: latest)
 *
 * Command type: diff_against_depot
 */
class UEEDITORMCP_API FDiffAgainstDepotAction : public FEditorAction
{
public:
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual FString GetActionName() const override { return TEXT("diff_against_depot"); }
	virtual bool RequiresSave() const override { return false; }

private:
	FString AssetPath;

	/** Convert EDiffType::Type enum to human-readable string */
	static FString DiffTypeToString(int32 DiffType);

	/** Convert EDiffType::Category enum to string */
	static FString DiffCategoryToString(int32 Category);
};

/**
 * FGetAssetHistoryAction
 *
 * Lists source-control revision history for a given asset.
 * Returns an array of revisions that actually modified the file
 * (up to the provider limit, typically 100 for SVN).
 *
 * Params:
 *   asset_path  (string, required)  — e.g. "/Game/P110_2/Blueprints/BP_Foo"
 *   max_count   (int, optional)     — max revisions to return (default: all available)
 *
 * Command type: get_asset_history
 */
class UEEDITORMCP_API FGetAssetHistoryAction : public FEditorAction
{
public:
	virtual TSharedPtr<FJsonObject> ExecuteInternal(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context) override;

protected:
	virtual bool Validate(const TSharedPtr<FJsonObject>& Params, FUEEditorContext& Context, FString& OutError) override;
	virtual FString GetActionName() const override { return TEXT("get_asset_history"); }
	virtual bool RequiresSave() const override { return false; }

private:
	FString AssetPath;
};
