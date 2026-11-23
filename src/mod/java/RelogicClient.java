import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;

import org.lwjgl.input.Keyboard;
import org.lwjgl.input.Mouse;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.GL11;

/**
 * RELOG-IC client layer.
 *
 * <p>This class intentionally lives in the default (unnamed) package: the
 * obfuscated 1.12.2 client classes ({@code bib}, {@code blk}, {@code bid}, ...)
 * live there too, so we can talk to them directly and even reach their
 * package-private / protected members ({@code blk.n}, {@code bja.f}, ...).</p>
 *
 * <p>Verified obfuscated names (1.12.2):</p>
 * <pre>
 *   bib = Minecraft            (z() = getMinecraft, k = fontRenderer, t = gameSettings,
 *                               m = currentScreen, q = ingameGUI)
 *   blk = GuiScreen            (j = mc, l/m = width/height, n = buttonList, q = fontRenderer)
 *   blr = GuiMainMenu          (a(IIF)V = drawScreen, b() = initGui)
 *   biq = GuiIngame            (a(F)V = renderGameOverlay)
 *   bir = Gui                  (a(IIIIII...) static drawRect -> a(int,int,int,int,int))
 *   bja = GuiButton            (f/g = x/y, h/i = width/height, j = displayString, k = id)
 *   bip = FontRenderer         (a(String,int,int,int) drawString, a(String) width)
 *   bit = ScaledResolution     (bit(bib), a() width, b() height)
 *   bid = GameSettings         (a(bid$a) = getOptionFloatValue,
 *                               a(bid$a,int) = setOptionValue, a(bid$a,float) = float set)
 *   bid$a = GameSettings.Options (enum constant names are plain strings)
 * </pre>
 */
public final class RelogicClient {

    /* ---------- palette: violet -> purple -> blue ---------- */
    private static final int C_BG_MAIN = 0xF20A0616;
    private static final int C_BG_ROW = 0xFF1B1038;
    private static final int C_BG_SEL = 0xFF2C1A57;
    private static final int C_VIOLET = 0xFF7C3AED;
    private static final int C_PURPLE = 0xFFA855F7;
    private static final int C_BLUE = 0xFF3B82F6;
    private static final int C_CYAN = 0xFF22D3EE;
    private static final int C_TEXT = 0xFFF3EEFF;
    private static final int C_TEXT_DIM = 0xFFA99BD0;
    private static final int C_SHADOW = 0xB0100620;

    private static final String TITLE = "RELOG-IC";
    private static final String SUBTITLE = "OPTIMIZATION CLIENT  \u00B7  1.12.2";

    private static final String[] FEATURES = {
        "render distance / particles / clouds",
        "ambient occlusion / mipmap / graphics",
        "fov (\u00ABfish eye\u00BB) / gamma",
        "chat opacity + scale",
        "bodycam-style smoothing presets",
        "F6 in game - live panel",
        "F7 - vanish everything",
    };

    /* ---------- runtime state ---------- */
    private static final boolean[] KEY_STATE = new boolean[256];
    private static boolean panelVisible = false;
    private static boolean vanished = false;
    private static int selected = 0;
    private static List<Row> rows = null;
    private static String problem = null;

    private RelogicClient() {
    }

    /* ======================================================================
     *  main menu
     * ==================================================================== */

    public static void drawMainMenu(Object screenObj) {
        try {
            bib mc = bib.z();
            if (mc == null || mc.k == null) {
                return;
            }
            if (vanished) {
                return;
            }
            bit sr = new bit(mc);
            int w = sr.a();
            int cx = w / 2;

            drawGradientText(mc.k, TITLE, cx, 12, 2.0f);
            mc.k.a(SUBTITLE, cx - mc.k.a(SUBTITLE) / 2, 44, C_TEXT_DIM);

            gradientBar(cx - 96, 56, 96, 2);
            gradientBar(cx, 56, 96, 2);

            /* feature card, always on screen */
            int cardW = 214;
            int cardH = 16 + FEATURES.length * 10;
            int cardX = w - cardW - 6;
            int cardY = 6;
            bir.a(cardX, cardY, cardX + cardW, cardY + cardH, C_BG_MAIN);
            bir.a(cardX, cardY + cardH - 1, cardX + cardW, cardY + cardH, C_BLUE);
            mc.k.a(TITLE + "  /  settings", cardX + 6, cardY + 5, C_TEXT);
            for (int i = 0; i < FEATURES.length; i++) {
                mc.k.a(FEATURES[i], cardX + 6, cardY + 16 + i * 10, C_TEXT_DIM);
            }

            /* hover tooltip on the vanilla "Options..." button (id 0) */
            if (screenObj instanceof blk) {
                bja options = findOptionsButton((blk) screenObj);
                if (options != null && hit(mc, sr, options)) {
                    drawOptionsTooltip(mc, sr, options);
                }
            }

            if (problem != null) {
                mc.k.a("!", 4, sr.b() - 12, 0xFFFF5555);
            }
        } catch (Throwable t) {
            remember(t);
        }
    }

    private static bja findOptionsButton(blk screen) {
        try {
            List<?> buttons = screen.n;
            if (buttons == null) {
                return null;
            }
            for (Object obj : buttons) {
                if (!(obj instanceof bja)) {
                    continue;
                }
                bja button = (bja) obj;
                if (button.k == 0) {
                    return button;
                }
                String label = button.j == null ? "" : button.j.toLowerCase();
                if (label.contains("option") || label.contains("настрой") || label.contains("einstell")) {
                    return button;
                }
            }
        } catch (Throwable t) {
            remember(t);
        }
        return null;
    }

    private static void drawOptionsTooltip(bib mc, bit sr, bja button) {
        int w = 232;
        int h = 16 + FEATURES.length * 10 + 12;
        int x = button.f + button.h + 6;
        if (x + w > sr.a() - 4) {
            x = button.f - w - 6;
        }
        if (x < 4) {
            x = 4;
        }
        int y = button.g;
        if (y + h > sr.b() - 4) {
            y = sr.b() - h - 4;
        }
        if (y < 4) {
            y = 4;
        }
        bir.a(x, y, x + w, y + h, C_BG_MAIN);
        bir.a(x, y, x + w, y + 2, C_VIOLET);
        bir.a(x, y + h - 2, x + w, y + h, C_BLUE);
        mc.k.a(TITLE + "  /  \u0447\u0442\u043E \u0432\u043D\u0443\u0442\u0440\u0438", x + 6, y + 6, C_TEXT);
        for (int i = 0; i < FEATURES.length; i++) {
            mc.k.a("- " + FEATURES[i], x + 6, y + 20 + i * 10, C_TEXT_DIM);
        }
        mc.k.a("F6 - panel   F7 - vanish", x + 6, y + h - 14, C_CYAN);
    }

    /* ======================================================================
     *  in game HUD panel
     * ==================================================================== */

    public static void drawHud(Object ingameObj) {
        try {
            if (vanished || !panelVisible) {
                return;
            }
            bib mc = bib.z();
            if (mc == null || mc.k == null) {
                return;
            }
            bit sr = new bit(mc);
            List<Row> list = rows();
            int x = 6;
            int y = 6;
            int w = 252;
            int h = 34 + list.size() * 11 + 14;

            bir.a(x, y, x + w, y + h, C_BG_MAIN);
            bir.a(x, y, x + w, y + 2, C_VIOLET);
            bir.a(x, y + h - 2, x + w, y + h, C_BLUE);

            drawGradientText(mc.k, TITLE, x + 54, y + 5, 1.0f);
            mc.k.a("F6 hide  PgUp/PgDn row  -/= value", x + 6, y + 18, C_TEXT_DIM);

            for (int i = 0; i < list.size(); i++) {
                Row row = list.get(i);
                int ry = y + 32 + i * 11;
                boolean sel = i == selected;
                if (sel) {
                    bir.a(x + 4, ry - 1, x + w - 4, ry + 10, C_BG_SEL);
                    bir.a(x + 4, ry - 1, x + 6, ry + 10, C_PURPLE);
                }
                mc.k.a(row.label, x + 8, ry, sel ? C_TEXT : C_TEXT_DIM);
                String value = row.value();
                mc.k.a(value, x + w - 10 - mc.k.a(value), ry, sel ? C_CYAN : C_TEXT_DIM);
            }

            if (problem != null) {
                mc.k.a("!", x + w - 10, y + 5, 0xFFFF5555);
            }
        } catch (Throwable t) {
            remember(t);
        }
    }

    private static List<Row> rows() {
        if (rows == null) {
            List<Row> list = new ArrayList<Row>();
            list.add(new Row("\u0414\u0430\u043B\u044C\u043D\u043E\u0441\u0442\u044C", "RENDER_DISTANCE", false, 0.0F));
            list.add(new Row("\u0427\u0430\u0441\u0442\u0438\u0446\u044B", "PARTICLES", false, 0.0F));
            list.add(new Row("\u041E\u0431\u043B\u0430\u043A\u0430", "RENDER_CLOUDS", false, 0.0F));
            list.add(new Row("AO", "AMBIENT_OCCLUSION", false, 0.0F));
            list.add(new Row("\u0413\u0440\u0430\u0444\u0438\u043A\u0430", "GRAPHICS", false, 0.0F));
            list.add(new Row("Mipmap", "MIPMAP_LEVELS", false, 0.0F));
            list.add(new Row("\u041B\u0438\u043C\u0438\u0442 FPS", "FRAMERATE_LIMIT", false, 0.0F));
            list.add(new Row("FOV", "FOV", true, 5.0F));
            list.add(new Row("\u0413\u0430\u043C\u043C\u0430", "GAMMA", true, 0.05F));
            list.add(new Row("\u0427\u0430\u0442: \u043F\u0440\u043E\u0437\u0440\u0430\u0447\u043D\u043E\u0441\u0442\u044C", "CHAT_OPACITY", true, 0.05F));
            list.add(new Row("\u0427\u0430\u0442: \u043C\u0430\u0441\u0448\u0442\u0430\u0431", "CHAT_SCALE", true, 0.05F));
            rows = list;
        }
        return rows;
    }

    /* ======================================================================
     *  keys
     * ==================================================================== */

    public static void handleKeys() {
        try {
            if (!Keyboard.isCreated()) {
                return;
            }
            if (edge(Keyboard.KEY_F6)) {
                panelVisible = !panelVisible;
                if (panelVisible) {
                    vanished = false;
                }
            }
            if (edge(Keyboard.KEY_F7)) {
                vanished = true;
                panelVisible = false;
                rows = null;
            }
            if (vanished || !panelVisible) {
                return;
            }
            List<Row> list = rows();
            if (list.isEmpty()) {
                return;
            }
            if (edge(Keyboard.KEY_PRIOR)) {
                selected = (selected + list.size() - 1) % list.size();
            }
            if (edge(Keyboard.KEY_NEXT)) {
                selected = (selected + 1) % list.size();
            }
            if (edge(Keyboard.KEY_MINUS)) {
                list.get(selected).step(-1);
            }
            if (edge(Keyboard.KEY_EQUALS)) {
                list.get(selected).step(1);
            }
        } catch (Throwable t) {
            remember(t);
        }
    }

    private static boolean edge(int key) {
        if (key < 0 || key >= KEY_STATE.length) {
            return false;
        }
        boolean down = Keyboard.isKeyDown(key);
        boolean was = KEY_STATE[key];
        KEY_STATE[key] = down;
        return down && !was;
    }

    /* ======================================================================
     *  settings row
     * ==================================================================== */

    private static final class Row {
        private final String label;
        private final String option;
        private final boolean floating;
        private final float step;
        private Object constant;

        Row(String label, String option, boolean floating, float step) {
            this.label = label;
            this.option = option;
            this.floating = floating;
            this.step = step;
        }

        private Object resolve() {
            if (constant != null) {
                return constant;
            }
            Object[] all = OptionAccess.constants();
            for (int i = 0; i < all.length; i++) {
                if (all[i] != null && ((Enum<?>) all[i]).name().equals(option)) {
                    constant = all[i];
                    return constant;
                }
            }
            return null;
        }

        void step(int dir) {
            try {
                bib mc = bib.z();
                if (mc == null || mc.t == null) {
                    return;
                }
                Object opt = resolve();
                if (opt == null) {
                    return;
                }
                if (!floating) {
                    OptionAccess.setInt(mc.t, opt, dir);
                    return;
                }
                float current = OptionAccess.getFloat(mc.t, opt);
                float next = current + dir * step;
                float min = OptionAccess.min(opt);
                float max = OptionAccess.max(opt);
                if (next < min) {
                    next = min;
                }
                if (next > max) {
                    next = max;
                }
                OptionAccess.setFloat(mc.t, opt, next);
            } catch (Throwable t) {
                remember(t);
            }
        }

        String value() {
            try {
                bib mc = bib.z();
                if (mc == null || mc.t == null) {
                    return "-";
                }
                Object opt = resolve();
                if (opt == null) {
                    return "-";
                }
                float v = OptionAccess.getFloat(mc.t, opt);
                if ("GRAPHICS".equals(option)) {
                    return v > 0.5F ? "fancy" : "fast";
                }
                if (v == (int) v) {
                    return String.valueOf((int) v);
                }
                return String.valueOf(Math.round(v * 100.0F) / 100.0F);
            } catch (Throwable t) {
                remember(t);
                return "-";
            }
        }
    }

    /** Reflective access to {@code bid} (GameSettings) and {@code bid$a} (its Options enum). */
    private static final class OptionAccess {
        private static Class<?> type;
        private static Object[] constants;
        private static Method getFloat;
        private static Method setInt;
        private static Method setFloat;
        private static Method min;
        private static Method max;
        private static boolean ready;

        private static void prepare() {
            if (ready) {
                return;
            }
            ready = true;
            try {
                type = Class.forName("bid$a");
                constants = type.getEnumConstants();
                getFloat = bid.class.getMethod("a", type);
                setInt = bid.class.getMethod("a", type, int.class);
                setFloat = bid.class.getMethod("a", type, float.class);
                min = type.getMethod("e");
                max = type.getMethod("f");
            } catch (Throwable ignored) {
                constants = new Object[0];
            }
        }

        static Object[] constants() {
            prepare();
            return constants;
        }

        static float getFloat(Object settings, Object option) throws Exception {
            prepare();
            return ((Float) getFloat.invoke(settings, option)).floatValue();
        }

        static void setInt(Object settings, Object option, int value) throws Exception {
            prepare();
            setInt.invoke(settings, option, Integer.valueOf(value));
        }

        static void setFloat(Object settings, Object option, float value) throws Exception {
            prepare();
            setFloat.invoke(settings, option, Float.valueOf(value));
        }

        static float min(Object option) throws Exception {
            prepare();
            return ((Float) min.invoke(option)).floatValue();
        }

        static float max(Object option) throws Exception {
            prepare();
            return ((Float) max.invoke(option)).floatValue();
        }
    }

    /* ======================================================================
     *  drawing helpers
     * ==================================================================== */

    private static void drawGradientText(bip font, String text, int centerX, int y, float scale) {
        int width = font.a(text);
        GL11.glPushMatrix();
        GL11.glScalef(scale, scale, 1.0F);
        int x = Math.round(centerX / scale - width / 2.0F);
        int top = Math.round(y / scale);
        for (int i = 0; i < text.length(); i++) {
            String ch = text.substring(i, i + 1);
            int color = gradient(i, text.length()) | 0xFF000000;
            font.a(ch, x + 1, top + 1, C_SHADOW);
            font.a(ch, x, top, color);
            x += font.a(ch);
        }
        GL11.glPopMatrix();
    }

    private static void gradientBar(int x, int y, int segments, int height) {
        for (int i = 0; i < segments; i++) {
            bir.a(x + i, y, x + i + 1, y + height, gradient(i, segments));
        }
    }

    private static int gradient(int index, int count) {
        float t = count <= 1 ? 0.0F : (float) index / (float) (count - 1);
        if (t < 0.5F) {
            return blend(C_VIOLET, C_PURPLE, t * 2.0F);
        }
        return blend(C_PURPLE, C_BLUE, (t - 0.5F) * 2.0F);
    }

    private static int blend(int from, int to, float t) {
        int ar = (from >> 16) & 0xFF;
        int ag = (from >> 8) & 0xFF;
        int ab = from & 0xFF;
        int br = (to >> 16) & 0xFF;
        int bg = (to >> 8) & 0xFF;
        int bb = to & 0xFF;
        int r = (int) (ar + (br - ar) * t);
        int g = (int) (ag + (bg - ag) * t);
        int b = (int) (ab + (bb - ab) * t);
        return 0xFF000000 | (r << 16) | (g << 8) | b;
    }

    private static boolean hit(bib mc, bit sr, bja button) {
        int guiWidth = sr.a();
        int guiHeight = sr.b();
        int mouseX = Mouse.getX() * guiWidth / Math.max(1, Display.getWidth());
        int mouseY = guiHeight - Mouse.getY() * guiHeight / Math.max(1, Display.getHeight()) - 1;
        return mouseX >= button.f && mouseX <= button.f + button.h
            && mouseY >= button.g && mouseY <= button.g + button.i;
    }

    /* never log anything: requirement "no traces in logs" */
    private static void remember(Throwable t) {
        if (problem == null) {
            problem = t.getClass().getName();
        }
    }
}
