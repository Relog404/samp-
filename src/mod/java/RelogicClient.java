import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
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
 * <p>Forge 1.12.2 runs the vanilla classes under <b>SRG names</b>
 * ({@code net.minecraft.client.Minecraft.func_71410_x}), not under the raw
 * obfuscated names from {@code client.jar} ({@code bib.z}), so this class
 * talks to the game purely through reflection with the SRG names taken from
 * the official {@code mcp-1.12.2-srg} mapping. Nothing here can break
 * class loading: every lookup is guarded and a failure only disables drawing.</p>
 *
 * <pre>
 *   net.minecraft.client.Minecraft                       func_71410_x()  getMinecraft
 *                                                        field_71466_p   fontRenderer
 *                                                        field_71474_y   gameSettings
 *                                                        field_71462_r   currentScreen
 *   net.minecraft.client.gui.GuiScreen                    field_146292_n  buttonList
 *                                                        field_146294_l  width
 *                                                        field_146295_m  height
 *   net.minecraft.client.gui.GuiButton                    field_146128_h  x
 *                                                        field_146129_i  y
 *                                                        field_146120_f  width
 *                                                        field_146121_g  height
 *                                                        field_146126_j  displayString
 *                                                        field_146127_k  id
 *   net.minecraft.client.gui.FontRenderer                 func_78276_b(String,int,int,int)
 *                                                        func_78256_a(String) -> width
 *   net.minecraft.client.gui.Gui                          func_73734_a(int,int,int,int,int)
 *   net.minecraft.client.gui.ScaledResolution             func_78326_a()/func_78328_b()
 *   net.minecraft.client.settings.GameSettings            func_74296_a(Options) -> float
 *                                                        func_74306_a(Options,int)
 *                                                        func_74304_a(Options,float)
 *   net.minecraft.client.settings.GameSettings$Options    enum, name() = RENDER_DISTANCE, ...
 * </pre>
 */
public final class RelogicClient {

    /* ================= SRG names (Forge 1.12.2 runtime) ================= */
    private static final String CLS_MC = "net.minecraft.client.Minecraft";
    private static final String CLS_FONT = "net.minecraft.client.gui.FontRenderer";
    private static final String CLS_BUTTON = "net.minecraft.client.gui.GuiButton";
    private static final String CLS_SCALED = "net.minecraft.client.gui.ScaledResolution";
    private static final String CLS_GUI = "net.minecraft.client.gui.Gui";
    private static final String CLS_SETTINGS = "net.minecraft.client.settings.GameSettings";
    private static final String CLS_OPTIONS = "net.minecraft.client.settings.GameSettings$Options";
    private static final String CLS_MAIN_MENU = "net.minecraft.client.gui.GuiMainMenu";

    private static final String M_GET_INSTANCE = "func_71410_x";
    private static final String M_DRAW_RECT = "func_73734_a";
    private static final String M_DRAW_STRING = "func_78276_b";
    private static final String M_STRING_WIDTH = "func_78256_a";
    private static final String M_SCALED_WIDTH = "func_78326_a";
    private static final String M_SCALED_HEIGHT = "func_78328_b";
    private static final String M_OPTION_GET_FLOAT = "func_74296_a";
    private static final String M_OPTION_SET_INT = "func_74306_a";
    private static final String M_OPTION_SET_FLOAT = "func_74304_a";
    private static final String M_SAVE_OPTIONS = "func_74303_b";

    private static final String F_FONT = "field_71466_p";
    private static final String F_SETTINGS = "field_71474_y";
    private static final String F_CURRENT_SCREEN = "field_71462_r";
    private static final String F_DISPLAY_WIDTH = "field_71443_c";
    private static final String F_DISPLAY_HEIGHT = "field_71440_d";
    private static final String F_BUTTON_LIST = "field_146292_n";
    private static final String F_SCREEN_WIDTH = "field_146294_l";
    private static final String F_SCREEN_HEIGHT = "field_146295_m";
    private static final String F_BTN_WIDTH = "field_146120_f";
    private static final String F_BTN_HEIGHT = "field_146121_g";
    private static final String F_BTN_X = "field_146128_h";
    private static final String F_BTN_Y = "field_146129_i";
    private static final String F_BTN_TEXT = "field_146126_j";
    private static final String F_BTN_ID = "field_146127_k";

    /* ================= palette: violet -> purple -> blue ================= */
    private static final int C_BG_MAIN = 0xF20A0616;
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

    /* ================= reflection handles ================= */
    private static boolean ready = false;
    private static boolean broken = false;

    private static Class<?> clsMc;
    private static Class<?> clsFont;
    private static Class<?> clsButton;
    private static Class<?> clsScaled;
    private static Class<?> clsOptions;

    private static Method mGetInstance;
    private static Method mDrawRect;
    private static Method mDrawString;
    private static Method mStringWidth;
    private static Method mScaledWidth;
    private static Method mScaledHeight;
    private static Method mOptionGetFloat;
    private static Method mOptionSetInt;
    private static Method mOptionSetFloat;
    private static Method mSaveOptions;
    private static Constructor<?> ctorScaled;

    private static Field fFont;
    private static Field fSettings;
    private static Field fCurrentScreen;
    private static Field fDisplayWidth;
    private static Field fDisplayHeight;
    private static Field fButtonList;
    private static Field fScreenWidth;
    private static Field fScreenHeight;
    private static Field fBtnWidth;
    private static Field fBtnHeight;
    private static Field fBtnX;
    private static Field fBtnY;
    private static Field fBtnText;
    private static Field fBtnId;

    /* ================= runtime state ================= */
    private static final boolean[] KEY_STATE = new boolean[256];
    private static boolean panelVisible = false;
    private static boolean vanished = false;
    private static int selected = 0;
    private static List<Row> rows = null;

    private RelogicClient() {
    }

    /* ======================================================================
     *  reflection bootstrap
     * ==================================================================== */

    private static synchronized boolean init() {
        if (ready) {
            return !broken;
        }
        ready = true;
        try {
            clsMc = Class.forName(CLS_MC);
            clsFont = Class.forName(CLS_FONT);
            clsButton = Class.forName(CLS_BUTTON);
            clsScaled = Class.forName(CLS_SCALED);
            clsOptions = Class.forName(CLS_OPTIONS);
            Class<?> clsGui = Class.forName(CLS_GUI);
            Class<?> clsSettings = Class.forName(CLS_SETTINGS);

            mGetInstance = clsMc.getMethod(M_GET_INSTANCE);
            fFont = field(clsMc, F_FONT);
            fSettings = field(clsMc, F_SETTINGS);
            fCurrentScreen = field(clsMc, F_CURRENT_SCREEN);
            fDisplayWidth = field(clsMc, F_DISPLAY_WIDTH);
            fDisplayHeight = field(clsMc, F_DISPLAY_HEIGHT);

            mDrawRect = clsGui.getMethod(M_DRAW_RECT, int.class, int.class, int.class, int.class, int.class);
            mDrawString = clsFont.getMethod(M_DRAW_STRING, String.class, int.class, int.class, int.class);
            mStringWidth = clsFont.getMethod(M_STRING_WIDTH, String.class);

            ctorScaled = clsScaled.getConstructor(clsMc);
            mScaledWidth = clsScaled.getMethod(M_SCALED_WIDTH);
            mScaledHeight = clsScaled.getMethod(M_SCALED_HEIGHT);

            Class<?> clsScreen = Class.forName("net.minecraft.client.gui.GuiScreen");
            fButtonList = field(clsScreen, F_BUTTON_LIST);
            fScreenWidth = field(clsScreen, F_SCREEN_WIDTH);
            fScreenHeight = field(clsScreen, F_SCREEN_HEIGHT);

            fBtnX = field(clsButton, F_BTN_X);
            fBtnY = field(clsButton, F_BTN_Y);
            fBtnWidth = field(clsButton, F_BTN_WIDTH);
            fBtnHeight = field(clsButton, F_BTN_HEIGHT);
            fBtnText = field(clsButton, F_BTN_TEXT);
            fBtnId = field(clsButton, F_BTN_ID);

            mOptionGetFloat = clsSettings.getMethod(M_OPTION_GET_FLOAT, clsOptions);
            mOptionSetInt = clsSettings.getMethod(M_OPTION_SET_INT, clsOptions, int.class);
            mOptionSetFloat = clsSettings.getMethod(M_OPTION_SET_FLOAT, clsOptions, float.class);
            mSaveOptions = clsSettings.getMethod(M_SAVE_OPTIONS);
        } catch (Throwable t) {
            broken = true;
        }
        return !broken;
    }

    private static Field field(Class<?> owner, String name) throws NoSuchFieldException {
        Field field = owner.getDeclaredField(name);
        field.setAccessible(true);
        return field;
    }

    private static Object mc() {
        try {
            return mGetInstance.invoke(null);
        } catch (Throwable t) {
            return null;
        }
    }

    private static Object font(Object mc) {
        return get(fFont, mc);
    }

    private static Object settings(Object mc) {
        return get(fSettings, mc);
    }

    private static Object get(Field field, Object owner) {
        try {
            return field == null || owner == null ? null : field.get(owner);
        } catch (Throwable t) {
            return null;
        }
    }

    /* ======================================================================
     *  drawing primitives (all reflective: SRG runtime names)
     * ==================================================================== */

    private static void rect(int x1, int y1, int x2, int y2, int color) {
        try {
            mDrawRect.invoke(null, Integer.valueOf(x1), Integer.valueOf(y1),
                    Integer.valueOf(x2), Integer.valueOf(y2), Integer.valueOf(color));
        } catch (Throwable ignored) {
            // never crash the render thread
        }
    }

    private static void text(Object font, String value, int x, int y, int color) {
        if (font == null || value == null) {
            return;
        }
        try {
            mDrawString.invoke(font, value, Integer.valueOf(x), Integer.valueOf(y), Integer.valueOf(color));
        } catch (Throwable ignored) {
            // ignore
        }
    }

    private static int textWidth(Object font, String value) {
        if (font == null || value == null) {
            return 0;
        }
        try {
            return ((Integer) mStringWidth.invoke(font, value)).intValue();
        } catch (Throwable t) {
            return value.length() * 6;
        }
    }

    /** ScaledResolution dims: [width, height]. */
    private static int[] guiSize(Object mc) {
        try {
            Object scaled = ctorScaled.newInstance(mc);
            int w = ((Integer) mScaledWidth.invoke(scaled)).intValue();
            int h = ((Integer) mScaledHeight.invoke(scaled)).intValue();
            return new int[] {w, h};
        } catch (Throwable t) {
            return new int[] {0, 0};
        }
    }

    private static int[] mouse(int guiWidth, int guiHeight) {
        try {
            int dw = Display.getWidth();
            int dh = Display.getHeight();
            if (dw <= 0 || dh <= 0) {
                return new int[] {0, 0};
            }
            int mx = Mouse.getX() * guiWidth / dw;
            int my = guiHeight - Mouse.getY() * guiHeight / dh - 1;
            return new int[] {mx, my};
        } catch (Throwable t) {
            return new int[] {0, 0};
        }
    }

    /* ======================================================================
     *  main menu
     * ==================================================================== */

    public static void drawMainMenu(Object screenObj) {
        try {
            if (vanished || !init()) {
                return;
            }
            Object mc = mc();
            if (mc == null) {
                return;
            }
            Object font = font(mc);
            if (font == null) {
                return;
            }
            int[] size = guiSize(mc);
            int w = size[0];
            if (w <= 0) {
                return;
            }
            int cx = w / 2;

            drawGradientText(font, TITLE, cx, 12, 2.0F);
            text(font, SUBTITLE, cx - textWidth(font, SUBTITLE) / 2, 44, C_TEXT_DIM);
            gradientBar(cx - 96, 56, 96, 2);
            gradientBar(cx, 56, 96, 2);

            int cardW = 214;
            int cardH = 16 + FEATURES.length * 10;
            int cardX = w - cardW - 6;
            int cardY = 6;
            rect(cardX, cardY, cardX + cardW, cardY + cardH, C_BG_MAIN);
            rect(cardX, cardY + cardH - 1, cardX + cardW, cardY + cardH, C_BLUE);
            text(font, TITLE + "  /  settings", cardX + 6, cardY + 5, C_TEXT);
            for (int i = 0; i < FEATURES.length; i++) {
                text(font, FEATURES[i], cardX + 6, cardY + 16 + i * 10, C_TEXT_DIM);
            }

            Object options = findOptionsButton(screenObj);
            if (options != null) {
                int[] mouse = mouse(size[0], size[1]);
                int bx = num(fBtnX, options);
                int by = num(fBtnY, options);
                int bw = num(fBtnWidth, options);
                int bh = num(fBtnHeight, options);
                if (mouse[0] >= bx && mouse[0] <= bx + bw && mouse[1] >= by && mouse[1] <= by + bh) {
                    drawOptionsTooltip(font, size, bx, by, bw);
                }
            }
        } catch (Throwable ignored) {
            // never crash the game
        }
    }

    private static Object findOptionsButton(Object screenObj) {
        if (screenObj == null || fButtonList == null) {
            return null;
        }
        try {
            Object list = fButtonList.get(screenObj);
            if (!(list instanceof List)) {
                return null;
            }
            Object fallback = null;
            for (Object element : (List<?>) list) {
                if (element == null || clsButton == null || !clsButton.isInstance(element)) {
                    continue;
                }
                if (num(fBtnId, element) == 0) {
                    return element;
                }
                Object label = get(fBtnText, element);
                String value = label == null ? "" : label.toString().toLowerCase();
                if (value.contains("option") || value.contains("\u043D\u0430\u0441\u0442\u0440\u043E\u0439")
                        || value.contains("einstell") || value.contains("optionen")) {
                    fallback = element;
                }
            }
            return fallback;
        } catch (Throwable t) {
            return null;
        }
    }

    private static void drawOptionsTooltip(Object font, int[] size, int bx, int by, int bw) {
        int w = 232;
        int h = 16 + FEATURES.length * 10 + 12;
        int x = bx + bw + 6;
        if (x + w > size[0] - 4) {
            x = bx - w - 6;
        }
        if (x < 4) {
            x = 4;
        }
        int y = by;
        if (y + h > size[1] - 4) {
            y = size[1] - h - 4;
        }
        if (y < 4) {
            y = 4;
        }
        rect(x, y, x + w, y + h, C_BG_MAIN);
        rect(x, y, x + w, y + 2, C_VIOLET);
        rect(x, y + h - 2, x + w, y + h, C_BLUE);
        text(font, TITLE + "  /  \u0447\u0442\u043E \u0432\u043D\u0443\u0442\u0440\u0438", x + 6, y + 6, C_TEXT);
        for (int i = 0; i < FEATURES.length; i++) {
            text(font, "- " + FEATURES[i], x + 6, y + 20 + i * 10, C_TEXT_DIM);
        }
        text(font, "F6 - panel   F7 - vanish", x + 6, y + h - 14, C_CYAN);
    }

    /* ======================================================================
     *  in game HUD panel
     * ==================================================================== */

    public static void drawHud(Object ingameObj) {
        try {
            if (vanished || !panelVisible || !init()) {
                return;
            }
            Object mc = mc();
            if (mc == null) {
                return;
            }
            Object font = font(mc);
            if (font == null) {
                return;
            }
            List<Row> list = rows();
            int x = 6;
            int y = 6;
            int w = 252;
            int h = 34 + list.size() * 11 + 14;

            rect(x, y, x + w, y + h, C_BG_MAIN);
            rect(x, y, x + w, y + 2, C_VIOLET);
            rect(x, y + h - 2, x + w, y + h, C_BLUE);

            drawGradientText(font, TITLE, x + 54, y + 5, 1.0F);
            text(font, "F6 hide  PgUp/PgDn row  -/= value", x + 6, y + 18, C_TEXT_DIM);

            Object settings = settings(mc);
            for (int i = 0; i < list.size(); i++) {
                Row row = list.get(i);
                int ry = y + 32 + i * 11;
                boolean sel = i == selected;
                if (sel) {
                    rect(x + 4, ry - 1, x + w - 4, ry + 10, C_BG_SEL);
                    rect(x + 4, ry - 1, x + 6, ry + 10, C_PURPLE);
                }
                text(font, row.label, x + 8, ry, sel ? C_TEXT : C_TEXT_DIM);
                String value = row.value(settings);
                text(font, value, x + w - 10 - textWidth(font, value), ry, sel ? C_CYAN : C_TEXT_DIM);
            }
        } catch (Throwable ignored) {
            // never crash the game
        }
    }

    private static List<Row> rows() {
        if (rows == null) {
            List<Row> list = new ArrayList<Row>();
            list.add(new Row("\u0414\u0430\u043B\u044C\u043D\u043E\u0441\u0442\u044C", "RENDER_DISTANCE", false, 0.0F, 0.0F, 0.0F));
            list.add(new Row("\u0427\u0430\u0441\u0442\u0438\u0446\u044B", "PARTICLES", false, 0.0F, 0.0F, 0.0F));
            list.add(new Row("\u041E\u0431\u043B\u0430\u043A\u0430", "RENDER_CLOUDS", false, 0.0F, 0.0F, 0.0F));
            list.add(new Row("AO", "AMBIENT_OCCLUSION", false, 0.0F, 0.0F, 0.0F));
            list.add(new Row("\u0413\u0440\u0430\u0444\u0438\u043A\u0430", "GRAPHICS", false, 0.0F, 0.0F, 0.0F));
            list.add(new Row("Mipmap", "MIPMAP_LEVELS", false, 0.0F, 0.0F, 0.0F));
            list.add(new Row("\u041B\u0438\u043C\u0438\u0442 FPS", "FRAMERATE_LIMIT", false, 0.0F, 0.0F, 0.0F));
            list.add(new Row("FOV", "FOV", true, 5.0F, 30.0F, 110.0F));
            list.add(new Row("\u0413\u0430\u043C\u043C\u0430", "GAMMA", true, 0.05F, 0.0F, 1.0F));
            list.add(new Row("\u0427\u0430\u0442: \u043F\u0440\u043E\u0437\u0440\u0430\u0447\u043D\u043E\u0441\u0442\u044C", "CHAT_OPACITY", true, 0.05F, 0.0F, 1.0F));
            list.add(new Row("\u0427\u0430\u0442: \u043C\u0430\u0441\u0448\u0442\u0430\u0431", "CHAT_SCALE", true, 0.05F, 0.0F, 1.0F));
            rows = list;
        }
        return rows;
    }

    /* ======================================================================
     *  keys
     * ==================================================================== */

    public static void handleKeys() {
        try {
            if (!Keyboard.isCreated() || vanished) {
                return;
            }
            if (edge(Keyboard.KEY_F6)) {
                panelVisible = !panelVisible;
            }
            if (edge(Keyboard.KEY_F7)) {
                vanished = true;
                panelVisible = false;
                rows = null;
                return;
            }
            if (!panelVisible || !init()) {
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
            Object mc = mc();
            Object settings = mc == null ? null : settings(mc);
            if (edge(Keyboard.KEY_MINUS)) {
                list.get(selected).step(settings, -1);
            }
            if (edge(Keyboard.KEY_EQUALS)) {
                list.get(selected).step(settings, 1);
            }
        } catch (Throwable ignored) {
            // never crash the game
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
        private final float min;
        private final float max;
        private Object constant;

        Row(String label, String option, boolean floating, float step, float min, float max) {
            this.label = label;
            this.option = option;
            this.floating = floating;
            this.step = step;
            this.min = min;
            this.max = max;
        }

        private Object resolve() {
            if (constant != null) {
                return constant;
            }
            try {
                Object[] all = clsOptions.getEnumConstants();
                if (all == null) {
                    return null;
                }
                for (int i = 0; i < all.length; i++) {
                    if (all[i] != null && ((Enum<?>) all[i]).name().equals(option)) {
                        constant = all[i];
                        return constant;
                    }
                }
            } catch (Throwable ignored) {
                // ignore
            }
            return null;
        }

        void step(Object settings, int dir) {
            if (settings == null) {
                return;
            }
            Object opt = resolve();
            if (opt == null) {
                return;
            }
            try {
                if (!floating) {
                    mOptionSetInt.invoke(settings, opt, Integer.valueOf(dir));
                    persist(settings);
                    return;
                }
                float current = ((Float) mOptionGetFloat.invoke(settings, opt)).floatValue();
                float next = current + dir * step;
                if (next < min) {
                    next = min;
                }
                if (next > max) {
                    next = max;
                }
                mOptionSetFloat.invoke(settings, opt, Float.valueOf(next));
                persist(settings);
            } catch (Throwable ignored) {
                // ignore
            }
        }

        private static void persist(Object settings) {
            try {
                mSaveOptions.invoke(settings);
            } catch (Throwable ignored) {
                // not critical
            }
        }

        String value(Object settings) {
            if (settings == null) {
                return "-";
            }
            Object opt = resolve();
            if (opt == null) {
                return "-";
            }
            try {
                float v = ((Float) mOptionGetFloat.invoke(settings, opt)).floatValue();
                if ("GRAPHICS".equals(option)) {
                    return v > 0.5F ? "fancy" : "fast";
                }
                if (v == (int) v) {
                    return String.valueOf((int) v);
                }
                return String.valueOf(Math.round(v * 100.0F) / 100.0F);
            } catch (Throwable ignored) {
                return "-";
            }
        }
    }

    /* ======================================================================
     *  drawing helpers
     * ==================================================================== */

    private static void drawGradientText(Object font, String value, int centerX, int y, float scale) {
        try {
            int width = textWidth(font, value);
            GL11.glPushMatrix();
            GL11.glScalef(scale, scale, 1.0F);
            int x = Math.round(centerX / scale - width / 2.0F);
            int top = Math.round(y / scale);
            for (int i = 0; i < value.length(); i++) {
                String ch = value.substring(i, i + 1);
                int color = gradient(i, value.length()) | 0xFF000000;
                text(font, ch, x + 1, top + 1, C_SHADOW);
                text(font, ch, x, top, color);
                x += textWidth(font, ch);
            }
            GL11.glPopMatrix();
        } catch (Throwable ignored) {
            // ignore
        }
    }

    private static void gradientBar(int x, int y, int segments, int height) {
        for (int i = 0; i < segments; i++) {
            rect(x + i, y, x + i + 1, y + height, gradient(i, segments));
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

    private static int num(Field field, Object owner) {
        Object value = get(field, owner);
        return value instanceof Number ? ((Number) value).intValue() : 0;
    }
}
