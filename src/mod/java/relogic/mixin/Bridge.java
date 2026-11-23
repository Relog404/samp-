package relogic.mixin;

import java.lang.reflect.Method;

/**
 * Reflective bridge between the mixins (packaged) and {@code RelogicClient}
 * (default package, so it can reach the obfuscated client classes directly).
 */
public final class Bridge {

    private static Method mainMenu;
    private static Method hud;
    private static Method keys;

    static {
        try {
            Class<?> client = Class.forName("RelogicClient");
            mainMenu = client.getMethod("drawMainMenu", Object.class);
            hud = client.getMethod("drawHud", Object.class);
            keys = client.getMethod("handleKeys");
        } catch (Throwable ignored) {
            // silently disabled - the game must never break because of us
        }
    }

    private Bridge() {
    }

    public static void mainMenu(Object screen) {
        call(mainMenu, screen);
    }

    public static void hud(Object ingame) {
        call(hud, ingame);
    }

    public static void keys() {
        call(keys);
    }

    private static void call(Method method, Object... args) {
        if (method == null) {
            return;
        }
        try {
            method.invoke(null, args);
        } catch (Throwable ignored) {
            // never log, never crash
        }
    }
}
