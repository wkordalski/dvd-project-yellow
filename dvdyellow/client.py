import os
from dvdyellow.game import *
import sfml as sf
from math import floor

data_directory = 'data'
fontCeltic = sf.Font.from_file(os.path.join(data_directory, "celtic.ttf"))
fontArial = sf.Font.from_file(os.path.join(data_directory, "arial.ttf"))
gra = None
figura = None
moja_tura = 0


# Przycisk
class Przycisk(sf.Drawable):
    def __init__(self, napis, x, y, minus_y=20, jasnosc=255, lenx=250, leny=60, fo=fontCeltic, color=sf.Color.BLACK,
                 style=sf.Text.BOLD, size=30):
        sf.Drawable.__init__(self)
        self.pole = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "czerwony.JPG")))
        self.pole.texture_rectangle = sf.Rectangle(sf.Vector2(x - lenx / 2, y - leny / 2), sf.Vector2(lenx, leny))
        self.pole.color = sf.Color(255, 255, 255, jasnosc)  # RGB, jasność
        self.pole.position = sf.Vector2(x - lenx / 2, y - leny / 2)
        self.tekst = sf.Text(napis)
        self.tekst.font = fo
        self.tekst.character_size = size
        self.tekst.style = style
        self.tekst.color = color
        self.tekst.position = x - 6.35 * len(napis), y - minus_y

    def zawiera(self, x, y):
        return self.pole.texture_rectangle.contains(sf.Vector2(x, y))

    def draw(self, target, states):
        target.draw(self.pole, states)
        target.draw(self.tekst, states)


def ustaw_gre(game):
    if game is not None:
        global gra
        gra = game
        gra.on_your_turn = zmiana_tury
        global figura
        figura = gra.get_transformable_pawn()


def txt(x, y, color=sf.Color.BLACK, size=25, fo=fontArial, tek=""):
    tekst = sf.Text(tek)
    tekst.font = fo
    tekst.character_size = size
    tekst.color = color
    tekst.position = x + 10, y + 10
    return tekst


def logowanie(session, lo, pa):
    session.sign_in(lo, pa)
    return session.get_signed_in_user().result


def rejestracja(session, lo, pa):
    return session.sign_up(lo, pa).result


def wylogowywanie(session):
    if session.get_signed_in_user().result:
        session.sign_out()


def zalogowani(session):
    return [u.name.result for u in session.get_waiting_room().result.get_online_users().result]


def wyjscie_z_menu(session):
    session.del_waiting_room().result


def rezygnacja(session):
    session.cancel_want_to_play().result


def przeciwnik():
    return gra.opponent.name.result


def zmiana_tury(game):
    print("Wywołano funkcję zmiana_tury")
    global moja_tura
    if moja_tura:
        moja_tura = 0
    else:
        moja_tura = 1


def main():
    global gra
    global figura

    w, h = sf.Vector2(800, 600)
    window = sf.RenderWindow(sf.VideoMode(w, h), "DVD Project Yellow Client")
    window.vertical_synchronization = True

    session = make_session('localhost').result
    ground = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "back.jpg")))

    GREY = sf.Color(195, 195, 195)

    # Pola klikalne na stronie startowej
    log = Przycisk("Log in", 400, 270, 20, 255)
    konto = Przycisk("Sign up", 400, 370, 20, 255)
    offline = Przycisk("Local game", 400, 470, 20, 255)

    # Pola do wpisania loginu i hasła
    login = Przycisk("Login", 400, 230, 70, 100, color=GREY)
    haslo = Przycisk("Password", 400, 330, 70, 100, color=GREY)

    # Pola klikalne na stronach logowania/rejestracji
    zaloguj = Przycisk("Log in", 400, 430, 20, 255)
    rejestruj = Przycisk("Sign up", 400, 430, 20, 255)
    menu = Przycisk("Menu", 400, 530, 20, 255)

    # Pola klikalne na stronie głównej
    nowa = Przycisk("New game", 145, 230, 20, 255)
    ranking = Przycisk("Ranking", 145, 310, 20, 255)
    przyjaciele = Przycisk("Friends", 145, 390, 20, 255)
    zmiany = Przycisk("Account settings", 145, 470, 20, 255)
    wyloguj = Przycisk("Log out", 145, 550, 20, 255)
    random = Przycisk("Random player", 650, 230, 20, 200, lenx=200)

    # Duża ramka na stronie głównej
    box = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "czerwony.JPG")))
    box.texture_rectangle = sf.Rectangle((10, 10), (450, 380))
    box.color = sf.Color(255, 255, 255, 100)  # RGB, jasność
    box.position = sf.Vector2(300, 200)

    # Napis na grze lokalnej
    lazy = txt(160, 200, color=GREY, size=35, fo=fontCeltic,
               tek="Error 404 - this page isn't available now, \nbecause programmers are too lazy. Sorry")

    # Nazwa gry
    game = txt(210, 50, color=GREY, size=100, fo=fontCeltic, tek="Domination")

    # Błędy
    logerror_txt = txt(140, 50, color=GREY, size=35, fo=fontCeltic,
                       tek="Sorry, your login or password is incorrect.\n                 Please try again")
    logerror = 0
    regerror_txt = txt(223, 50, color=GREY, size=35, fo=fontCeltic,
                       tek="This login is already used.\n       Please try again")
    regerror = 0

    # Waiting
    wait = txt(250, 250, color=GREY, size=35, fo=fontCeltic, tek="Waiting for opponent")

    # GAME
    big_box = Przycisk("", 500, 300, 0, 255, lenx=560, leny=560)
    big_box2 = Przycisk("", 500, 300, 0, 255, lenx=550, leny=550, color=sf.Color(73, 99, 135, 255))
    finish = Przycisk("Finish game", 110, 50, 20, 255, 180, 60)

    # Game over
    won = txt(250, 250, color=GREY, size=35, fo=fontCeltic, tek="Congratulations, you won!")
    defeated = txt(250, 250, color=GREY, size=35, fo=fontCeltic, tek="Sorry, you defeated. Next time will be better!")
    draw = txt(250, 250, color=GREY, size=35, fo=fontCeltic, tek="Draw, no one won!")


    logg = txt(275, 200)
    pas = txt(275, 300)
    password = ""
    moj_login = ""

    chosen = 0  # 1-login, 2-password
    actual = 0  # 0-page0, 1-logowanie, 2-rejestracja, 3-gra lokalna, 4-menu główne, 5-gra
    option = 0  # 1-new game, 2- ranking, 3-friends, 4-settings

    x, y = 0, 0

    session.on_game_found = ustaw_gre

    while window.is_open:
        # SIEĆ
        session.process_events()

        for event in window.events:
            if event == sf.MouseMoveEvent:
                x, y = event.position

            if event == sf.CloseEvent:
                if actual in (4, 5):
                    if actual == 4:
                        wyjscie_z_menu(session)
                    else:
                        gra.abandon().result
                    wylogowywanie(session)
                window.close()

            # ZABAWY MYSZKĄ
            elif event == sf.MouseButtonEvent and event.pressed:
                # STRONA STARTOWA
                if actual == 0:
                    chosen = 0
                    if log.zawiera(x, y):
                        actual = 1
                    if konto.zawiera(x, y):
                        actual = 2
                    if offline.zawiera(x, y):
                        actual = 3

                # LOGOWANIE
                elif actual == 1:
                    if menu.zawiera(x, y):
                        actual = 0
                        logerror = 0
                        logg.string = ""
                        pas.string = ""
                        password = ""
                    elif zaloguj.zawiera(x, y):
                        if logowanie(session, logg.string, password):
                            actual = 4
                            logerror = 0
                            moj_login = logg.string
                            logg.string = ""
                            pas.string = ""
                            password = ""
                        else:
                            actual = 1
                            logerror = 1

                    elif login.zawiera(x, y):
                        chosen = 1
                    elif haslo.zawiera(x, y):
                        chosen = 2
                    else:
                        chosen = 0

                # REJESTRACJA
                elif actual == 2:
                    if menu.zawiera(x, y):
                        actual = 0
                        regerror = 0
                        logg.string = ""
                        pas.string = ""
                        password = ""
                    elif rejestruj.zawiera(x, y):
                        if rejestracja(session, logg.string, password):
                            actual = 0
                            regerror = 0
                            logg.string = ""
                            pas.string = ""
                            password = ""
                        else:
                            actual = 2
                            regerror = 1
                    elif login.zawiera(x, y):
                        chosen = 1
                    elif haslo.zawiera(x, y):
                        chosen = 2
                    else:
                        chosen = 0

                elif actual == 3:
                    if menu.zawiera(x, y):
                        actual = 0

                # STRONA GŁÓWNA GRY
                elif actual == 4:
                    if option == 1 and random.zawiera(x, y):
                        option = 0
                        actual = 5
                        wyjscie_z_menu(session)
                        ustaw_gre(session.set_want_to_play().result)
                    elif nowa.zawiera(x, y):
                        option = 1
                    elif ranking.zawiera(x, y):
                        option = 2
                    elif przyjaciele.zawiera(x, y):
                        option = 3
                    elif zmiany.zawiera(x, y):
                        option = 4
                    elif menu.zawiera(x, y):
                        wyjscie_z_menu(session)
                        wylogowywanie(session)
                        moj_login = ""
                        actual = 0
                        option = 0
                    else:
                        pass

                # GRA WŁAŚCIWA
                elif actual == 5:
                    if gra:
                        if finish.zawiera(x, y):
                            actual = 4
                            gra.abandon().result
                        if moja_tura:
                            xx = int((x - 250) / (wym - 1))
                            yy = int((y - 50) / (wym - 1))
                            if 0 <= xx < gra.width and 0 <= yy < gra.height and gra.move((xx, yy), figura).result:
                                zmiana_tury(gra)


            # ZABAWY KLAWIATURĄ
            elif event == sf.TextEvent:
                if chosen == 1:
                    if len(logg.string) < 9 and 33 <= event.unicode <= 126:
                        logg.string += chr(event.unicode)
                    elif event.unicode == 8:
                        logg.string = logg.string[0:-1]
                elif chosen == 2:
                    if len(pas.string) < 22 and 33 <= event.unicode <= 126:
                        pas.string += "*"
                        password += chr(event.unicode)
                    elif event.unicode == 8:
                        pas.string = pas.string[0:-1]
                        password = password[0:-1]

            # ZABAWY KLAWIATURĄ CZ. II
            elif actual in (1, 2, 5) and event == sf.KeyEvent and event.released:
                if event.code == sf.Keyboard.RETURN:
                    if actual == 1:
                        if logowanie(session, logg.string, password):
                            actual = 4
                            logerror = 0
                            logg.string = ""
                            pas.string = ""
                            password = ""
                        else:
                            actual = 1
                            logerror = 1
                    elif actual == 2:
                        if rejestracja(session, logg.string, password):
                            actual = 0
                            regerror = 0
                            logg.string = ""
                            pas.string = ""
                            password = ""
                        else:
                            actual = 2
                            regerror = 1
                elif actual in (1, 2) and event.code == sf.Keyboard.TAB:
                    chosen = (chosen + 1) % 3
                elif actual == 5 and event.code == sf.Keyboard.RIGHT:
                    figura.rotate_clockwise()
                elif actual == 5 and event.code == sf.Keyboard.LEFT:
                    figura.rotate_clockwise()
                    figura.rotate_clockwise()
                    figura.rotate_clockwise()

        if not window.is_open:
            break

        window.clear()
        window.draw(ground)
        if actual == 1 or actual == 2:
            if chosen == 1:
                login.pole.color = sf.Color(255, 255, 255, 200)
                haslo.pole.color = sf.Color(255, 255, 255, 100)
            elif chosen == 2:
                login.pole.color = sf.Color(255, 255, 255, 100)
                haslo.pole.color = sf.Color(255, 255, 255, 200)
            else:
                login.pole.color = sf.Color(255, 255, 255, 100)
                haslo.pole.color = sf.Color(255, 255, 255, 100)

            window.draw(login)
            window.draw(haslo)
            window.draw(menu)
            window.draw(logg)
            window.draw(pas)

        if actual == 1:
            if logerror:
                window.draw(logerror_txt)
            window.draw(zaloguj)

        if actual == 2:
            if regerror:
                window.draw(regerror_txt)
            window.draw(rejestruj)

        if actual == 4:
            window.draw(game)
            window.draw(nowa)
            window.draw(ranking)
            window.draw(przyjaciele)
            window.draw(zmiany)
            window.draw(wyloguj)
            if option == 1:
                window.draw(box)
                heading = txt(300, 200, tek="Online Players", size=33, fo=fontCeltic)
                window.draw(heading)
                window.draw(random)
                counter = 0
                for gamer in zalogowani(session):
                    player = Przycisk(gamer, 525, 295 + 50 * counter, 20, 100, lenx=450, leny=40, fo=fontArial,
                                      color=sf.Color.WHITE, style=sf.Text.REGULAR)
                    window.draw(player)
                    counter += 1

        if actual == 5:
            if not gra:
                window.draw(wait)
            elif gra.is_finished:
                    if gra.result == 'won':
                        window.draw(won)
                    elif gra.result == 'defeated':
                        window.draw(defeated)
                    elif gra.result == 'draw':
                        window.draw(draw)
            else:
                window.draw(big_box)
                window.draw(big_box2)
                window.draw(finish)

                kol1 = sf.Color(255, 255, 0, 255)
                kol1b = sf.Color(255, 255, 0, 150)
                kol2 = sf.Color(64, 32, 192, 255)
                kol2b = sf.Color(64, 32, 192, 150)

                play1 = txt(20, 80, tek=moj_login, size=42, fo=fontCeltic, color=kol1)
                res1 = txt(20, 130, tek=str(gra.player_points[gra.player_number - 1]), size=42, fo=fontCeltic,
                           color=kol1)
                play2 = txt(20, 500, tek=przeciwnik(), size=42, fo=fontCeltic, color=kol2)
                res2 = txt(20, 450, tek=str(gra.player_points[2 - gra.player_number]), size=42, fo=fontCeltic,
                           color=kol2)

                fig_y = figura.height
                fig_x = figura.width

                list_fig = []
                czy_zielona = 1

                wym = 500 / max(gra.width, gra.height)

                kwadrat = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "black.jpg")))
                kwadrat.texture_rectangle = sf.Rectangle((10, 10), (wym, wym))

                """
                -3 - pole nieistniejące
                -2, -1 - pola zablokowane przez graczy 1 i 2
                0 - wolne pole na planszy
                1, 2 - pola przykryte przez graczy 1 i 2
                """
                poz_y = 0
                while poz_y < gra.height:
                    poz_x = 0
                    while poz_x < gra.width:
                        if y < 50 + (poz_y + 1) * wym and y + (fig_y - 1) * wym > 50 + poz_y * wym and x < 250 + (
                            poz_x + 1) * wym \
                                and x + (fig_x - 1) * wym > 250 + poz_x * wym \
                                and figura.get_pawn_point(floor((250 - x) / wym + poz_x + 1),
                                                          floor((50 - y) / wym + poz_y + 1)) \
                                and y + (fig_y - 1) * wym <= 50 + gra.height * wym and y >= 50 \
                                and x + (fig_x - 1) * wym <= 250 + gra.width * wym and x >= 250 and moja_tura:
                            if gra.get_field(poz_x, poz_y)[0] != 0:
                                czy_zielona = 0
                            list_fig.append((250 + poz_x * (wym - 1), 50 + poz_y * (wym - 1)))
                        if gra.get_field(poz_x, poz_y)[0] == 0:
                            kwadrat.color = sf.Color(255, 255, 255, 255)
                        elif gra.get_field(poz_x, poz_y)[0] == 1:
                            kwadrat.color = kol1
                        elif gra.get_field(poz_x, poz_y)[0] == -1:
                            kwadrat.color = kol1b
                        elif gra.get_field(poz_x, poz_y)[0] == 2:
                            kwadrat.color = kol2
                        elif gra.get_field(poz_x, poz_y)[0] == -2:
                            kwadrat.color = kol2b
                        elif gra.get_field(poz_x, poz_y)[0] == -3:
                            kwadrat.color = sf.Color(255, 255, 255, 0)

                        kwadrat.position = sf.Vector2(250 + poz_x * (wym - 1), 50 + poz_y * (wym - 1))
                        window.draw(kwadrat)
                        if gra.get_field(poz_x, poz_y)[1] < 0:
                            numerek = txt(250 + poz_x * (wym - 1) + wym / 8, 50 + poz_y * (wym - 1),
                                          tek=str(gra.get_field(poz_x, poz_y)[1]), size=wym * 3 / 5)
                        else:
                            numerek = txt(250 + poz_x * (wym - 1) + wym / 5, 50 + poz_y * (wym - 1),
                                          tek=str(gra.get_field(poz_x, poz_y)[1]), size=wym * 3 / 5)
                        if gra.get_field(poz_x, poz_y)[0] != -3:
                            window.draw(numerek)
                        poz_x += 1
                    poz_y += 1

                for poz in list_fig:
                    if czy_zielona:
                        kwadrat.color = sf.Color.GREEN
                    else:
                        kwadrat.color = sf.Color.RED
                    kwadrat.position = sf.Vector2(poz[0], poz[1])
                    window.draw(kwadrat)

                window.draw(play1)
                window.draw(play2)
                window.draw(res1)
                window.draw(res2)

                window.draw(play1)
                window.draw(play2)
                window.draw(res1)
                window.draw(res2)

        # Error 404
        if actual == 3:
            window.draw(game)
            window.draw(lazy)
            window.draw(menu)

        if actual == 0:
            window.draw(game)
            window.draw(log)
            window.draw(konto)
            window.draw(offline)

        window.display()


if __name__ == "__main__":
    main()
