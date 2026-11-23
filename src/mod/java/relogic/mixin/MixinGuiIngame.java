package relogic.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** GuiIngame.renderGameOverlay = {@code func_175180_a(F)V} in the SRG runtime. */
@Mixin(targets = "biq")
public class MixinGuiIngame {

    @Inject(method = "func_175180_a(F)V", at = @At("TAIL"), remap = false, require = 0)
    private void relogic$renderOverlaySrg(float partialTicks, CallbackInfo ci) {
        Bridge.hud(this);
    }

    @Inject(method = "a(F)V", at = @At("TAIL"), remap = false, require = 0)
    private void relogic$renderOverlayNotch(float partialTicks, CallbackInfo ci) {
        Bridge.hud(this);
    }
}
