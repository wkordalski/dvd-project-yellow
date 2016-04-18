import os

import sfml as sf


class ResourceManager:
    def __init__(self, data_directory):
        self.data_directory = data_directory
        self.fonts = dict()
        self.textures = dict()

    def font(self, name, reload=False):
        if name not in self.fonts or reload:
            self.fonts[name] = sf.Font.from_file(os.path.join(self.data_directory, name))
        return self.fonts[name]

    def texture(self, name, reload=False):
        if name not in self.fonts or reload:
            self.fonts[name] = sf.Texture.from_file(os.path.join(self.data_directory, name))
        return self.fonts[name]

resources = ResourceManager('data')


class Window:
    def __init__(self, title, size):
        w, h = size
        self.window = sf.RenderWindow(sf.VideoMode(w, h), title)
        self.window.vertical_synchronization = True

        self.view = MainMenuView(self)

    def set_view(self, view):
        self.view = view

    def close(self):
        self.window.close()

    def run(self):
        mouse = sf.Vector2(-1, -1)
        while self.window.is_open:
            for event in self.window.events:
                if event == sf.CloseEvent:
                    self.window.close()
                if event == sf.MouseMoveEvent:
                    mouse = event.position

                if event == sf.MouseButtonEvent and event.pressed:
                    self.view.on_click(mouse)

                if event == sf.TextEvent:
                    self.view.on_text(chr(event.unicode))

            self.window.clear()
            self.view.draw(self.window)
            self.window.display()


class Widget:
    def on_text(self, character):
        pass

    def on_click(self):
        pass


class Button(Widget):
    def __init__(self, parent, text, position, size):
        self.position = position
        self.size = size
        self.text = text
        self.on_click_handler = None
        self.parent = parent

        x, y = position
        w, h = size

        self.rectangle_shape = sf.RectangleShape(sf.Vector2(w, h))
        self.rectangle_shape.fill_color = sf.Color(255, 0, 0, 190)
        self.rectangle_shape.position = sf.Vector2(x, y)

        self.text_shape = sf.Text(text)
        self.text_shape.position = sf.Vector2(x + w/2, y + h/2)
        self.text_shape.font = resources.font('celtic.ttf')
        self.text_shape.character_size = 30
        self.text_shape.style = sf.Text.BOLD
        self.text_shape.color = sf.Color.BLACK

        lx, ly, lw, lh = self.text_shape.local_bounds
        self.text_shape.origin = sf.Vector2((lw+lx)/2, (lh+ly)/2)

    def is_point_over(self, point):
        x, y = point
        x1, y1 = self.position
        x2, y2 = self.size
        x2 += x1
        y2 += y1
        return x1 <= x < x2 and y1 <= y < y2

    def draw(self, canvas):
        canvas.draw(self.rectangle_shape)
        canvas.draw(self.text_shape)

    def on_click(self):
        self.focus()
        if self.on_click_handler:
            self.on_click_handler()

    def on_focus(self):
        self.rectangle_shape.fill_color = sf.Color.RED

    def on_blur(self):
        self.rectangle_shape.fill_color = sf.Color(255, 0, 0, 190)

    def focus(self):
        self.on_focus()
        self.parent.focus(self)

    def blur(self):
        self.on_blur()


class TextBox(Widget):
    def __init__(self, parent, position, size, placeholder_text=''):
        self.position = position
        self.size = size
        self.placeholder_text = placeholder_text
        self.text = ''
        self.on_click_handler = None
        self.parent = parent

        x, y = position
        w, h = size

        self.rectangle_shape = sf.RectangleShape(sf.Vector2(w, h))
        self.rectangle_shape.fill_color = sf.Color(255, 0, 0, 190)
        self.rectangle_shape.position = sf.Vector2(x, y)

        self.text_shape = sf.Text()
        self.text_shape.position = sf.Vector2(x+8, y + h/2)
        self.text_shape.font = resources.font('arial.ttf')
        self.text_shape.character_size = 30
        self.text_shape.color = sf.Color.BLACK

    def _refresh_text(self):
        self.text_shape.string = self.text
        lx, ly, lw, lh = self.text_shape.local_bounds
        self.text_shape.origin = sf.Vector2(0, (lh+ly)/2)

    def is_point_over(self, point):
        x, y = point
        x1, y1 = self.position
        x2, y2 = self.size
        x2 += x1
        y2 += y1
        return x1 <= x < x2 and y1 <= y < y2

    def draw(self, canvas):
        canvas.draw(self.rectangle_shape)
        canvas.draw(self.text_shape)

    def on_click(self):
        self.focus()

    def on_text(self, character):
        if character == '\b':
            if len(self.text) > 0:
                self.text = self.text[:-1]
        elif character in ['\n', '\t']:
            pass
        else:
            self.text += character

        self._refresh_text()

    def on_focus(self):
        self.rectangle_shape.fill_color = sf.Color.RED

    def on_blur(self):
        self.rectangle_shape.fill_color = sf.Color(255, 0, 0, 190)

    def focus(self):
        self.on_focus()
        self.parent.focus(self)

    def blur(self):
        self.on_blur()


class PasswordBox(TextBox):
    def _refresh_text(self):
        self.text_shape.string = "*" * len(self.text)
        lx, ly, lw, lh = self.text_shape.local_bounds
        self.text_shape.origin = sf.Vector2(0, (lh+ly)/2)


class Image(Widget):
    def __init__(self, parent, image, position):
        self.parent = parent
        self.image = image
        self.position = position
        self.texture = resources.texture(image)
        self.size = self.texture.size

        self.sprite = sf.Sprite(self.texture)
        self.sprite.position = position

    def draw(self, canvas):
        canvas.draw(self.sprite)

    def is_point_over(self, point):
        x, y = point
        x1, y1 = self.position
        x2, y2 = self.size
        x2 += x1
        y2 += y1
        return x1 <= x < x2 and y1 <= y < y2


class View:
    def __init__(self):
        self.widgets = []
        self.focused = None

    def draw(self, canvas):
        for widget in self.widgets:
            widget.draw(canvas)

    def on_click(self, point):
        for widget in reversed(self.widgets):
            if widget.is_point_over(point):
                widget.on_click()
                break

    def focus(self, widget=None):
        if self.focused and self.focused != widget:
            self.focused.blur()
        self.focused = widget

    def blur(self):
        if self.focused:
            self.focused.blur()
        self.focused = None

    def on_text(self, character):
        if self.focused:
            self.focused.on_text(character)


class SignInView(View):
    def __init__(self, window):
        super(SignInView, self).__init__()
        self.window = window

        self.background = Image(self, 'back.jpg', (0,0))

        self.txt_login = TextBox(self, (100, 100), (200, 48))
        self.txt_password = PasswordBox(self, (100, 180), (200, 48))

        self.btn_ok = Button(self, "OK", (100, 260), (200, 48))
        self.btn_cancel = Button(self, "Menu", (100, 340), (200, 48))

        def show_menu():
            window.set_view(MainMenuView(window))
        self.btn_cancel.on_click_handler = show_menu

        self.widgets = [self.background, self.btn_ok, self.btn_cancel, self.txt_login, self.txt_password]


class SignUpView(View):
    def __init__(self, window):
        super(SignUpView, self).__init__()
        self.window = window

        self.background = Image(self, 'back.jpg', (0,0))

        self.txt_login = TextBox(self, (100, 100), (200, 48))
        self.txt_password = PasswordBox(self, (100, 180), (200, 48))

        self.btn_ok = Button(self, "OK", (100, 260), (200, 48))
        self.btn_cancel = Button(self, "Menu", (100, 340), (200, 48))

        def show_menu():
            window.set_view(MainMenuView(window))
        self.btn_cancel.on_click_handler = show_menu

        self.widgets = [self.background, self.btn_ok, self.btn_cancel, self.txt_login, self.txt_password]


class MainMenuView(View):
    def __init__(self, window):
        super(MainMenuView, self).__init__()
        self.window = window

        self.background = Image(self, 'back.jpg', (0,0))

        self.btn_sign_in = Button(self, "Zaloguj", (100, 100), (200, 48))

        def show_sign_in():
            window.set_view(SignInView(window))
        self.btn_sign_in.on_click_handler = show_sign_in

        self.btn_sign_up = Button(self, "Zarejestruj", (100, 180), (200, 48))

        def show_sign_up():
            window.set_view(SignUpView(window))
        self.btn_sign_up.on_click_handler = show_sign_up

        self.btn_exit = Button(self, "Wyjscie", (100, 260), (200, 48))

        def do_exit():
            window.close()
        self.btn_exit.on_click_handler = do_exit

        self.widgets = [self.background, self.btn_sign_in, self.btn_sign_up, self.btn_exit]


def main():
    wnd = Window('DVD Yellow test', (600, 600))
    wnd.run()


if __name__ == "__main__":
    main()
