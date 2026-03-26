#pragma once

#include "CoreMinimal.h"

class FEditorAction;

class UEBRIDGEEDITOR_API FUEEditorActionRegistry
{
public:
	static void RegisterDefaultActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers);
};
