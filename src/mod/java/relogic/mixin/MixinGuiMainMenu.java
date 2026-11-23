package relogic.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * {@code blr} = GuiMainMenu, {@code a(IIF)V} = drawScreen(int, int, float).
 */
@Mixin(targets = "blr", remap = false)
public class MixinGuiMainMenu {

    @Inject(method = "a(IIF)V", at = @At("TAIL"), remap = false)
    private void relogic$drawScreen(int mouseX, int mouseY, float partialTicks, CallbackInfo ci) {
        Bridge.mainMenu(this);
    }
}
