package relogic.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * {@code bib} = Minecraft, {@code t()V} = runTick().
 */
@Mixin(targets = "bib", remap = false)
public class MixinMinecraft {

    @Inject(method = "t()V", at = @At("TAIL"), remap = false)
    private void relogic$runTick(CallbackInfo ci) {
        Bridge.keys();
    }
}
