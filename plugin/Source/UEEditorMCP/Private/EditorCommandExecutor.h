#pragma once

#include "CoreMinimal.h"

class FJsonObject;
class UMCPBridge;

class FEditorCommandExecutor
{
public:
	static FString ExecuteGetContext(UMCPBridge* Bridge);
	static FString ExecuteCommand(UMCPBridge* Bridge, const FString& CommandType, TSharedPtr<FJsonObject> Params);
};
