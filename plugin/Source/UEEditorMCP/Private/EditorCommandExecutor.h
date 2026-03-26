#pragma once

#include "CoreMinimal.h"

class FJsonObject;
class UUEEditorBridge;

class FEditorCommandExecutor
{
public:
	static FString ExecuteGetContext(UUEEditorBridge* Bridge);
	static FString ExecuteCommand(UUEEditorBridge* Bridge, const FString& CommandType, TSharedPtr<FJsonObject> Params);
};
