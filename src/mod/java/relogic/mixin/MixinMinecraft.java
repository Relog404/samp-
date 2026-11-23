package relogic.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Minecraft.runTick = {@code func_71407_l()V} in the SRG runtime. */
@Mixin(targets = "bib")
public class MixinMinecraft {

    @Inject(method = "func_71407_l()V", at = @At("TAIL"), remap = false, require = 0)
    private void relogic$runTickSrg(CallbackInfo ci) {
        Bridge.keys();
    }

    @Inject(method = "t()V", at = @At("TAIL"), remap = false, require = 0)
    private void relogic$runTickNotch(CallbackInfo ci) {
        Bridge.keys();
    }
}
