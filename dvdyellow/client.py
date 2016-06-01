import os
from dvdyellow.game import *
import sfml as sf
from math import floor

data_directory = 'data'
fontCeltic = sf.Font.from_file(os.path.join(data_directory, "celtic.ttf"))
fontArial = sf.Font.from_file(os.path.join(data_directory, "arial.ttf"))
gra = None
figura = None
session = None
moja_tura = 0


# Przycisk
class Przycisk(sf.Drawable):
    def __init__(self, napis, x, y, minus_y=20, jasnosc=255, lenx=250, leny=60, fo=fontCeltic, color=sf.Color.BLACK,
                 style=sf.Text.BOLD, size=30, texture="czerwony.JPG"):
        sf.Drawable.__init__(self)
        self.pole = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, texture)))
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
        global gra, figura, moja_tura
        gra = game
        gra.on_your_turn = zmiana_tury
        moja_tura = 1 if gra.player_number == 1 else 0
        figura = gra.get_transformable_pawn()


def txt(x, y, color=sf.Color.BLACK, size=25, fo=fontArial, tek="", style=sf.Text.REGULAR):
    tekst = sf.Text(tek)
    tekst.font = fo
    tekst.character_size = size
    tekst.style = style
    tekst.color = color
    tekst.position = x + 10, y + 10
    return tekst


def przeslij(typ, fi, sec):
    if typ == 1:
        ustaw_sesje(fi, sec)
    elif typ == 2:
        session.sign_in(fi, sec)
        return session.get_signed_in_user().result
    elif typ == 3:
        return session.sign_up(fi, sec).result


def wylogowywanie():
    if session.get_signed_in_user().result:
        session.sign_out()


def zalogowani():
    return [u.name.result for u in session.get_waiting_room().result.get_online_users().result]


def lista_rankingowa():
    return [u[0].name.result for u in session.get_waiting_room().result.get_ranking().result]


def wyjscie_z_menu():
    session.del_waiting_room().result


def rezygnacja():
    session.cancel_want_to_play().result


def przeciwnik():
    return gra.opponent.name.result


def zmiana_tury(game):
    global moja_tura
    if moja_tura:
        moja_tura = 0
    else:
        moja_tura = 1


def rysuj(window, *args):
    for a in args:
        window.draw(a)


def ustaw_sesje(host, port):
    global session
    try:
        session = make_session(host, int(port)).result
    except:
        return 0
    session.on_game_found = ustaw_gre
    return 1


def main():
    # ZMIENNE WYSTĘPUJĄCE NA WIELU STRONACH
    global gra, figura, session
    ground = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "back.jpg")))
    GREY = sf.Color(195, 195, 195)
    menu = Przycisk("Menu", 400, 530, 20, 255)
    actual = 0  # 0 - strona startowa, 1 - wybór serwera, 2 - logowanie, 3 - rejestracja, 4-menu główne, 5-gra sieciowa, 6 - gra lokalna
    game = txt(210, 50, color=GREY, size=100, fo=fontCeltic, tek="Domination")
    x, y = 0, 0

    w, h = sf.Vector2(800, 600)
    window = sf.RenderWindow(sf.VideoMode(w, h), "DVD Project Yellow Client")
    window.vertical_synchronization = True

    # STRONA STARTOWA (PRZED / PO WYBORZE SERWERA)
    web = Przycisk("Web game", 400, 270, 20, 255)
    local = Przycisk("Local game", 400, 370, 20, 255)
    exit = Przycisk("Exit", 400, 470, 20, 255)
    disconnect = Przycisk("Disconnect", 400, 470, 20, 255)
    log = Przycisk("Log in", 400, 270, 20, 255)
    konto = Przycisk("Sign up", 400, 370, 20, 255)


    # WYBÓR SERWERA + LOGOWANIE + REJESTRACJA
    host = Przycisk("Address", 400, 230, 70, 100, color=GREY)
    port = Przycisk("Port", 400, 330, 70, 100, color=GREY)
    login = Przycisk("Login", 400, 230, 70, 100, color=GREY)
    haslo = Przycisk("Password", 400, 330, 70, 100, color=GREY)

    host_txt = txt(275, 200, tek="localhost", color=sf.Color(255, 255, 255, 200), style=sf.Text.ITALIC)
    port_txt = txt(275, 300, tek="42371", color=sf.Color(255, 255, 255, 200), style=sf.Text.ITALIC)
    login_txt = txt(275, 200)
    haslo_txt = txt(275, 300)  # gwiazdki

    moje_haslo = ""
    moj_login = ""

    polacz = Przycisk("Connect", 400, 430, 20, 255)
    submit = Przycisk("Log in", 400, 430, 20, 255), Przycisk("Sign up", 400, 430, 20, 255)

    connerror_txt = txt(140, 50, color=GREY, size=35, fo=fontCeltic,
            tek="Sorry, this address or port is incorrect.\n                 Please try again")
    error_txt = txt(140, 50, color=GREY, size=35, fo=fontCeltic,
                    tek="Sorry, your login or password is incorrect.\n                 Please try again"), \
                txt(223, 50, color=GREY, size=35, fo=fontCeltic,
                    tek="This login is already used.\n       Please try again")
    error = 0
    chosen = 0 # 1 - login/host, 2 - hasło/port


    # MENU GŁÓWNE (WAITING ROOM)
    nowa = Przycisk("New game", 145, 230, 20, 255)
    ranking = Przycisk("Ranking", 145, 310, 20, 255)
    przyjaciele = Przycisk("Friends", 145, 390, 20, 255)
    zmiany = Przycisk("Account settings", 145, 470, 20, 255)
    wyloguj = Przycisk("Log out", 145, 550, 20, 255)
    random = Przycisk("Random player", 650, 230, 20, 200, lenx=200)
    box = Przycisk("", 525, 390, lenx=450, leny=380, jasnosc=100)
    option = 0  # 1-new game, 2- ranking, 3-friends, 4-settings

    # GRA PRZEZ SIEĆ
    big_box = Przycisk("", 500, 300, 0, 255, lenx=560, leny=560)
    big_box2 = Przycisk("", 500, 300, 0, 255, lenx=550, leny=550, color=sf.Color(73, 99, 135, 255))
    finish = Przycisk("Finish game", 110, 50, 20, 255, 180, 60)

    while window.is_open:
        if session:
            session.process_events()

        for event in window.events:
            if event == sf.MouseMoveEvent:
                x, y = event.position

            # STRONA STARTOWA
            if actual == 0:
                # Zamykanie
                if event == sf.CloseEvent:
                    window.close()
                # Klikanie
                elif event == sf.MouseButtonEvent and event.released:
                    # serwer już wprowadzony
                    if session:
                        if log.zawiera(x, y):
                            actual = 2
                        elif konto.zawiera(x, y):
                            actual = 3
                        elif disconnect.zawiera(x, y):
                            session = None
                    # lub nie
                    else:
                        if web.zawiera(x, y):
                            actual = 1
                        elif local.zawiera(x, y):
                            actual = 6
                        elif exit.zawiera(x, y):
                            window.close()



            # WYBÓR SERWERA
            elif actual == 1:
                # Zamykanie
                if event == sf.CloseEvent:
                    window.close()

                # Klikanie + klawiatura
                elif event == sf.MouseButtonEvent and event.released:
                    if menu.zawiera(x, y):
                        actual = 0
                        host_txt.string = "localhost"
                        host_txt.color = sf.Color(255, 255, 255, 200)
                        host_txt.style = sf.Text.ITALIC
                        port_txt.string = "42371"
                        port_txt.color = sf.Color(255, 255, 255, 200)
                        port_txt.style = sf.Text.ITALIC
                        error = 0
                    elif polacz.zawiera(x, y):
                        if ustaw_sesje(host_txt.string, port_txt.string):
                            actual = 0
                            host_txt.string = "localhost"
                            host_txt.color = sf.Color(255, 255, 255, 200)
                            host_txt.style = sf.Text.ITALIC
                            port_txt.string = "42371"
                            port_txt.color = sf.Color(255, 255, 255, 200)
                            port_txt.style = sf.Text.ITALIC
                            error = 0
                        else:
                            error = 1

                    if host.zawiera(x, y):
                        chosen = 1

                    elif port.zawiera(x, y):
                        chosen = 2
                        if port_txt.color == sf.Color(255, 255, 255, 200):
                            port_txt.color = sf.Color.BLACK
                            port_txt.style = sf.Text.REGULAR
                            port_txt.string = ""
                    else:
                        chosen = 0

                # Wpisywanie tekstu
                elif event == sf.TextEvent:
                    if chosen == 1:
                        if len(host_txt.string) < 15 and 33 <= event.unicode <= 126:
                            host_txt.string += chr(event.unicode)
                        elif event.unicode == 8:
                            host_txt.string = host_txt.string[0:-1]
                    elif chosen == 2:
                        if len(port_txt.string) < 15 and 33 <= event.unicode <= 126:
                            port_txt.string += chr(event.unicode)
                        elif event.unicode == 8:
                            port_txt.string = port_txt.string[0:-1]


                # Klawiatura
                elif event == sf.KeyEvent and event.released:
                    if event.code == sf.Keyboard.RETURN:
                        if ustaw_sesje(host_txt.string, port_txt.string):
                            actual = 0
                            error = 0
                            host_txt.string = ""
                            port_txt.string = ""
                        else:
                            error = 1
                    elif event.code == sf.Keyboard.TAB:
                        chosen = (chosen + 1) % 3


            # LOGOWANIE + REJESTRACJA
            elif actual in (2, 3):
                # Zamykanie
                if event == sf.CloseEvent:
                    window.close()

                # Klikanie
                elif event == sf.MouseButtonEvent and event.released:
                    if menu.zawiera(x, y):
                        actual = 0
                        error = 0
                        login_txt.string = ""
                        port_txt.string = ""
                        moje_haslo = ""
                        moj_login = ""
                    elif submit[actual - 2].zawiera(x, y):
                        if przeslij(actual, login_txt.string, moje_haslo):
                            actual = 4 if actual == 2 else 0
                            error = 0
                            moj_login = login_txt.string
                            login_txt.string = ""
                            haslo_txt.string = ""
                            moje_haslo = ""
                        else:
                            error = 1

                    if login.zawiera(x, y):
                        chosen = 1
                    elif haslo.zawiera(x, y):
                        chosen = 2
                    else:
                        chosen = 0

                # Wpisywanie tekstu
                elif event == sf.TextEvent:
                    if chosen == 1:
                        if len(login_txt.string) < 9 and 33 <= event.unicode <= 126:
                            login_txt.string += chr(event.unicode)
                        elif event.unicode == 8:
                            login_txt.string = login_txt.string[0:-1]
                    elif chosen == 2:
                        if len(haslo_txt.string) < 22 and 33 <= event.unicode <= 126:
                            haslo_txt.string += "*"
                            moje_haslo += chr(event.unicode)
                        elif event.unicode == 8:
                            haslo_txt.string = haslo_txt.string[0:-1]
                            moje_haslo = moje_haslo[0:-1]

                # Klawiatura
                elif event == sf.KeyEvent and event.released:
                    if event.code == sf.Keyboard.RETURN:
                        if przeslij(actual, login_txt.string, moje_haslo):
                            actual = 4 if actual == 2 else 0
                            error = 0
                            moj_login = login_txt.string
                            login_txt.string = ""
                            haslo_txt.string = ""
                            moje_haslo = ""
                        else:
                            error = 1
                    elif event.code == sf.Keyboard.TAB:
                        chosen = (chosen + 1) % 3

            # MENU GŁÓWNE
            elif actual == 4:
                # Zamykanie
                if event == sf.CloseEvent:
                    wyjscie_z_menu()
                    wylogowywanie()
                    window.close()

                # Klikanie
                elif event == sf.MouseButtonEvent and event.released:
                    if option == 1 and random.zawiera(x, y):
                        option = 0
                        actual = 5
                        wyjscie_z_menu()
                        ustaw_gre(session.set_want_to_play().result)
                    elif nowa.zawiera(x, y):
                        option = 1
                    elif ranking.zawiera(x, y):
                        option = 2
                    elif przyjaciele.zawiera(x, y):
                        option = 3
                    elif zmiany.zawiera(x, y):
                        option = 4
                    elif wyloguj.zawiera(x, y):
                        wyjscie_z_menu()
                        wylogowywanie()
                        moj_login = ""
                        actual = 0
                        option = 0


            # GRA PRZEZ SIEĆ
            elif actual == 5:
                # Zamykanie
                if event == sf.CloseEvent:
                    wylogowywanie()
                    window.close()
                if not gra:  # czekanie
                    # Klikanie
                    if event == sf.MouseButtonEvent and event.released:
                        if menu.zawiera(x, y):
                            actual = 4
                            rezygnacja()

                elif not gra.is_finished:  # trwa rozgrywka
                    # Klikanie
                    if event == sf.MouseButtonEvent and event.released:
                        if finish.zawiera(x, y):
                            actual = 4
                            gra.abandon().result
                            gra = None
                        if moja_tura:
                            xx = int((x - 250) / (wym - 1))
                            yy = int((y - 50) / (wym - 1))
                            if 0 <= xx < gra.width and 0 <= yy < gra.height and gra.move((xx, yy), figura).result:
                                zmiana_tury(gra)

                    # Obracanie figury
                    elif event == sf.KeyEvent and event.released:
                        if event.code == sf.Keyboard.RIGHT:
                            figura.rotate_clockwise()
                        elif event.code == sf.Keyboard.LEFT:
                            figura.rotate_clockwise()
                            figura.rotate_clockwise()
                            figura.rotate_clockwise()

                else:  # rozgrywka skończona
                    # Klikanie
                    if event == sf.MouseButtonEvent and event.released:
                        if menu.zawiera(x, y):
                            actual = 4
                            gra = None


            # GRA LOKALNA
            elif actual == 6:
                # Zamykanie
                if event == sf.CloseEvent:
                    window.close()

                # Klikanie
                elif event == sf.MouseButtonEvent and event.released:
                    if menu.zawiera(x, y):
                        actual = 0


        if not window.is_open:
            break
        window.clear()
        rysuj(window, ground)


        # STRONA STARTOWA
        if actual == 0:
            if session:
                rysuj(window, game, log, konto, disconnect)
            else:
                rysuj(window, game, web, local, exit)


        # WYBÓR SERWERA
        elif actual == 1:
            if chosen == 1:
                host.pole.color = sf.Color(255, 255, 255, 200)
                port.pole.color = sf.Color(255, 255, 255, 100)
                if host_txt.color == sf.Color(255, 255, 255, 200):
                    host_txt.color = sf.Color.BLACK
                    host_txt.style = sf.Text.REGULAR
                    host_txt.string = ""
            elif chosen == 2:
                host.pole.color = sf.Color(255, 255, 255, 100)
                port.pole.color = sf.Color(255, 255, 255, 200)
                if port_txt.color == sf.Color(255, 255, 255, 200):
                    port_txt.color = sf.Color.BLACK
                    port_txt.style = sf.Text.REGULAR
                    port_txt.string = ""
            else:
                host.pole.color = sf.Color(255, 255, 255, 100)
                port.pole.color = sf.Color(255, 255, 255, 100)

            rysuj(window, host, port, menu, host_txt, port_txt, polacz)
            if error:
                rysuj(window, connerror_txt)


        # LOGOWANIE + REJESTRACJA
        elif actual in (2, 3):
            if chosen == 1:
                login.pole.color = sf.Color(255, 255, 255, 200)
                haslo.pole.color = sf.Color(255, 255, 255, 100)
            elif chosen == 2:
                login.pole.color = sf.Color(255, 255, 255, 100)
                haslo.pole.color = sf.Color(255, 255, 255, 200)
            else:
                login.pole.color = sf.Color(255, 255, 255, 100)
                haslo.pole.color = sf.Color(255, 255, 255, 100)

            rysuj(window, login, haslo, menu, login_txt, haslo_txt, submit[actual - 2])
            if error:
                rysuj(window, error_txt[actual - 2])


        # MENU GŁÓWNE
        elif actual == 4:
            rysuj(window, game, nowa, ranking, przyjaciele, zmiany, wyloguj)
            if option == 1:
                heading = txt(300, 200, tek="Online Players", size=33, fo=fontCeltic)
                rysuj(window, box, heading, random)
                counter = 0
                for gamer in zalogowani():
                    player = Przycisk(gamer, 525, 295 + 50 * counter, 20, 100, lenx=450, leny=40, fo=fontArial,
                                      color=sf.Color.WHITE, style=sf.Text.REGULAR)
                    rysuj(window, player)
                    counter += 1
            elif option == 2:
                heading = txt(475, 200, tek="Ranking", size=33, fo=fontCeltic)
                h_name = Przycisk("Name", 412, 295, 20, 100, lenx=224, leny=40, fo=fontArial,
                                      color=GREY, style=sf.Text.REGULAR)
                h_score = Przycisk("Score", 638, 295, 20, 100, lenx=224, leny=40, fo=fontArial,
                                      color=GREY, style=sf.Text.REGULAR)
                rysuj(window, box, heading, h_name, h_score)
                counter = 1
                for gamer in lista_rankingowa():
                    player = Przycisk(gamer, 412, 295 + 50 * counter, 20, 100, lenx=224, leny=40, fo=fontArial,
                                      color=sf.Color.WHITE, style=sf.Text.REGULAR)
                    points = Przycisk("1000", 638, 295 + 50 * counter, 20, 100, lenx=224, leny=40, fo=fontArial,
                                      color=sf.Color.WHITE, style=sf.Text.REGULAR)
                    rysuj(window, player, points)
                    counter += 1
            elif option != 0:
                rysuj(window, box)

        # GRA PRZEZ SIEĆ
        elif actual == 5:
            if not gra:  # czekanie
                wait = txt(250, 250, color=GREY, size=35, fo=fontCeltic, tek="Waiting for opponent")
                rysuj(window, wait, menu)

            elif gra.is_finished:  # koniec gry
                score = txt(250, 350, color=GREY, size=35, fo=fontCeltic,
                            tek="Your score: " + str(gra.player_points[gra.player_number - 1])
                                + "\nOpponent's score: " + str(gra.player_points[2 - gra.player_number]))
                result = {
                    'won': txt(250, 250, color=GREY, size=35, fo=fontCeltic, tek="Congratulations, you won!"),
                    'defeated': txt(250, 250, color=GREY, size=35, fo=fontCeltic, tek="Sorry, you defeated. \nNext time will be better!"),
                    'draw': txt(250, 250, color=GREY, size=35, fo=fontCeltic, tek="Draw, no one won!")
                }

                rysuj(window, result[gra.result], score, menu)

            else:  # rozgrywka

                rysuj(window, big_box, big_box2, finish)

                kol1 = sf.Color(255, 255, 0, 255)
                kol1b = sf.Color(255, 255, 0, 150)
                kol2 = sf.Color(64, 32, 192, 255)
                kol2b = sf.Color(64, 32, 192, 150)

                play_upp = txt(20, 80, tek=moj_login, size=42, fo=fontCeltic,
                               color=(kol1 if gra.player_number == 1 else kol2))
                res_upp = txt(20, 130, tek=str(gra.player_points[gra.player_number - 1]), size=42, fo=fontCeltic,
                              color=(kol1 if gra.player_number == 1 else kol2))
                play_low = txt(20, 500, tek=przeciwnik(), size=42, fo=fontCeltic,
                               color=(kol2 if gra.player_number == 1 else kol1))
                res_low = txt(20, 450, tek=str(gra.player_points[2 - gra.player_number]), size=42, fo=fontCeltic,
                              color=(kol2 if gra.player_number == 1 else kol1))

                list_fig = []
                czy_zielona = 1

                wym = int(500 / max(gra.width, gra.height))

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
                        if y < 50 + (poz_y + 1) * wym and y + (figura.height - 1) * wym > 50 + poz_y * wym \
                                and x < 250 + (poz_x + 1) * wym \
                                and x + (figura.width - 1) * wym > 250 + poz_x * wym \
                                and figura.get_pawn_point(floor((250 - x) / wym + poz_x + 1),
                                                          floor((50 - y) / wym + poz_y + 1)) \
                                and y + (figura.height - 1) * wym <= 50 + gra.height * wym and y >= 50 \
                                and x + (figura.width - 1) * wym <= 250 + gra.width * wym and x >= 250 and moja_tura:
                            if gra.get_field(poz_x, poz_y)[0] != 0:
                                czy_zielona = 0
                            list_fig.append((250 + poz_x * (wym - 1), 50 + poz_y * (wym - 1)))
                        else:
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
                            rysuj(window, kwadrat)
                        if gra.get_field(poz_x, poz_y)[1] < 0:
                            numerek = txt(250 + poz_x * (wym - 1) + wym / 8, 50 + poz_y * (wym - 1),
                                          tek=str(gra.get_field(poz_x, poz_y)[1]), size=wym * 3 / 5)
                        else:
                            numerek = txt(250 + poz_x * (wym - 1) + wym / 5, 50 + poz_y * (wym - 1),
                                          tek=str(gra.get_field(poz_x, poz_y)[1]), size=wym * 3 / 5)
                        if gra.get_field(poz_x, poz_y)[0] != -3:
                            rysuj(window, numerek)
                        poz_x += 1
                    poz_y += 1

                for poz in list_fig:
                    if czy_zielona:
                        kwadrat.color = sf.Color(0, 255, 0, 200)
                    else:
                        kwadrat.color = sf.Color(255, 0, 0, 200)
                    kwadrat.position = sf.Vector2(poz[0], poz[1])
                    rysuj(window, kwadrat)

                rysuj(window, play_upp, play_low, res_upp, res_low)


        # GRA LOKALNA
        elif actual == 6:
            lazy = txt(160, 200, color=GREY, size=35, fo=fontCeltic,
               tek="Error 404 - this page isn't available now, \nbecause programmers are too lazy. Sorry")
            rysuj(window, game, lazy, menu)

        window.display()


if __name__ == "__main__":
    main()
