#pragma once

#include "CoreMinimal.h"

class FEditorAction;

class UEEDITORMCP_API FUEEditorActionRegistry
{
public:
	static void RegisterDefaultActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers);
};
