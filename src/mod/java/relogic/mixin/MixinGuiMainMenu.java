package relogic.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * GuiMainMenu. Forge 1.12.2 renames the vanilla classes to SRG names at
 * runtime (verified in a real launch log), so the injection targets
 * {@code func_73863_a} (= drawScreen). The notch-named twin is kept as a
 * harmless fallback ({@code require = 0}) for obfuscated runtimes.
 */
@Mixin(targets = "blr")
public class MixinGuiMainMenu {

    @Inject(method = "func_73863_a(IIF)V", at = @At("TAIL"), remap = false, require = 0)
    private void relogic$drawScreenSrg(int mouseX, int mouseY, float partialTicks, CallbackInfo ci) {
        Bridge.mainMenu(this);
    }

    @Inject(method = "a(IIF)V", at = @At("TAIL"), remap = false, require = 0)
    private void relogic$drawScreenNotch(int mouseX, int mouseY, float partialTicks, CallbackInfo ci) {
        Bridge.mainMenu(this);
    }
}
