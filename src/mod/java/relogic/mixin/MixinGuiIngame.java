package relogic.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * {@code biq} = GuiIngame, {@code a(F)V} = renderGameOverlay(float).
 */
@Mixin(targets = "biq", remap = false)
public class MixinGuiIngame {

    @Inject(method = "a(F)V", at = @At("TAIL"), remap = false)
    private void relogic$renderGameOverlay(float partialTicks, CallbackInfo ci) {
        Bridge.hud(this);
    }
}
