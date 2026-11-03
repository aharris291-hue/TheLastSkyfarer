// The Last Skyfarer: menu buttons.

#include "LSMenu.h"

#include "Components/Button.h"
#include "LSUIHelpers.h"

UButton* LSUI::MakeMenuButton(UWidgetTree* Tree, const FText& Label, int32 Size, UObject* Owner,
	TArray<TObjectPtr<ULSClickProxy>>& Keep, TFunction<void()> Fn, UTextBlock** OutLabel)
{
	UButton* B = Tree->ConstructWidget<UButton>();
	FButtonStyle Style = B->GetStyle();
	Style.Normal.TintColor = FSlateColor(FLinearColor(0.12f, 0.1f, 0.08f, 1.f));
	Style.Hovered.TintColor = FSlateColor(FLinearColor(0.32f, 0.25f, 0.13f, 1.f));
	Style.Pressed.TintColor = FSlateColor(FLinearColor(0.45f, 0.35f, 0.16f, 1.f));
	B->SetStyle(Style); // buttons are focusable by default, so the gamepad can move between them
	UTextBlock* Text = MakeText(Tree, Label, Size);
	Text->SetAutoWrapText(false);
	B->AddChild(Text);
	ULSClickProxy* Proxy = NewObject<ULSClickProxy>(Owner);
	Proxy->Fn = MoveTemp(Fn);
	Keep.Add(Proxy);
	B->OnClicked.AddDynamic(Proxy, &ULSClickProxy::Click);
	if (OutLabel)
	{
		*OutLabel = Text;
	}
	return B;
}
