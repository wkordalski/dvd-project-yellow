import os
from dvdyellow.game import *
import sfml as sf
from math import floor

data_directory = 'data'
font = sf.Font.from_file(os.path.join(data_directory, "celtic.ttf"))
font2 = sf.Font.from_file(os.path.join(data_directory, "arial.ttf"))
gra = None
waiting = 0

# przycisk
def przycisk(napis, x, y, minus_y, jasnosc, lenx=250, leny=60, fo=font, color=sf.Color.BLACK, style=sf.Text.BOLD):
    pole = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "czerwony.JPG")))
    pole.texture_rectangle = sf.Rectangle((10, 10), (lenx, leny))
    pole.color = sf.Color(255, 255, 255, jasnosc)  # RGB, jasność
    pole.position = sf.Vector2(x-lenx/2, y-leny/2)
    tekst = sf.Text(napis)
    tekst.font = fo
    tekst.character_size = 30
    tekst.style = style
    tekst.color = color
    tekst.position = x-6.35*len(napis), y-minus_y
    return pole, tekst


def stop_waiting(game):
    global waiting
    waiting = 0
    global gra
    gra = game


def txt(x, y, color=sf.Color.BLACK, size=25, fo=font2, tek=""):
    tekst = sf.Text(tek)
    tekst.font = fo
    tekst.character_size = size
    tekst.color = color
    tekst.position = x+10, y+10
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


def wykonaj_ruch(gra, x, y):
    gra.move((x, y), gra.get_transformable_pawn())


def nowa_gra(session):
    return session.set_want_to_play().result


def rezygnacja(session):
    session.cancel_want_to_play().result


def przeciwnik(gra):
    return gra.opponent.name.result


def main():
    global gra
    global waiting

    w, h = sf.Vector2(800, 600)
    window = sf.RenderWindow(sf.VideoMode(w, h), "DVD Project Yellow Client")
    window.vertical_synchronization = True

    session = make_session('localhost').result
    ground = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "back.jpg")))

    GREY = sf.Color(195, 195, 195)

    # Pola klikalne na stronie startowej
    log, log_txt = przycisk("Log in", 400, 270, 20, 255)
    konto, konto_txt = przycisk("Sign up", 400, 370, 20, 255)
    offline, offline_txt = przycisk("Local game", 400, 470, 20, 255)

    # Pola do wpisania loginu i hasła
    login, login_txt = przycisk("Login", 400, 230, 70, 100)
    login_txt.color = GREY
    haslo, haslo_txt = przycisk("Password", 400, 330, 70, 100)
    haslo_txt.color = GREY

    # Pola klikalne na stronach logowania/rejestracji
    zaloguj, zaloguj_txt = przycisk("Log in", 400, 430, 20, 255)
    rejestruj, rejestruj_txt = przycisk("Sign up", 400, 430, 20, 255)
    menu, menu_txt = przycisk("Menu", 400, 530, 20, 255)

    # Pola klikalne na stronie głównej
    nowa, nowa_txt = przycisk("New game", 145, 230, 20, 255)
    ranking, ranking_txt = przycisk("Ranking", 145, 310, 20, 255)
    przyjaciele, przyjaciele_txt = przycisk("Friends", 145, 390, 20, 255)
    zmiany, zmiany_txt = przycisk("Account settings", 145, 470, 20, 255)
    wyloguj, wyloguj_txt = przycisk("Log out", 145, 550, 20, 255)

    # Duża ramka na stronie głównej
    box = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "czerwony.JPG")))
    box.texture_rectangle = sf.Rectangle((10, 10), (450, 380))
    box.color = sf.Color(255, 255, 255, 100)  # RGB, jasność
    box.position = sf.Vector2(300, 200)

    # Napis na grze lokalnej
    lazy = sf.Text("Error 404 - this page isn't available now, \nbecause programmers are too lazy. Sorry")
    lazy.font = font
    lazy.character_size = 35
    lazy.color = GREY
    lazy.position = 160, 200

    # Nazwa gry
    game = sf.Text("Nazwa gry")
    game.font = font
    game.character_size = 100
    game.color = GREY
    game.position = 210, 50

    # Błędy
    logerror_txt = txt(140, 50, color=GREY, size=35, fo=font)
    logerror_txt.string = "Sorry, your login or password is incorrect.\n                 Please try again"
    logerror = 0
    regerror_txt = txt(223, 50, color=GREY, size=35, fo=font)
    regerror_txt.string = "This login is already used.\n       Please try again"
    regerror = 0


    # Waiting
    wait = txt(250, 250, color = GREY, size = 35, fo=font, tek="Waiting for opponent")

    # GAME
    big_box,spam = przycisk("", 500, 300, 0, 255, lenx=560, leny=560)
    big_box2,spam = przycisk("", 500, 300, 0, 255, lenx=550, leny=550)
    big_box.color = sf.Color(73, 99, 135, 255)
    finish,finish_txt = przycisk("Finish game", 110, 50, 20, 255, 180, 60)





    logg = txt(275, 200)
    pas = txt(275, 300)
    password = ""

    chosen = 0  # 1-login, 2-password
    actual = 0  # 0-page0, 1-logowanie, 2-rejestracja, 3-gra lokalna, 4-menu główne, 5-gra
    option = 0  # 1-new game, 2- ranking, 3-friends, 4-settings

    x, y = 0, 0

    session.on_game_found = stop_waiting

    while window.is_open:
        # SIEĆ
        session.process_events()

        for event in window.events:
            if event == sf.MouseMoveEvent:
                x, y = event.position

            if event == sf.CloseEvent:
                if actual == 4:
                    wyjscie_z_menu(session)
                if actual in (4, 5):
                    wylogowywanie(session)
                window.close()

            # ZABAWY MYSZKĄ
            elif event == sf.MouseButtonEvent and event.pressed:
                # STRONA STARTOWA
                if actual == 0:
                    chosen = 0
                    if 275 <= x <= 525 and 240 <= y <= 300:
                        actual = 1
                    if 275 <= x <= 525 and 340 <= y <= 400:
                        actual = 2
                    if 275 <= x <= 525 and 440 <= y <= 500:
                        actual = 3

                # LOGOWANIE
                elif actual == 1:
                    if 275 <= x <= 525 and 500 <= y <= 560:
                        actual = 0
                        logerror = 0
                        logg.string = ""
                        pas.string = ""
                        password = ""
                    elif 275 <= x <= 525 and 400 <= y <= 460:
                        if logowanie(session, logg.string, password):
                            actual = 4
                            logerror = 0
                            logg.string = ""
                            pas.string = ""
                            password = ""
                        else:
                            actual = 1
                            logerror = 1

                    elif 275 <= x <= 525 and 200 <= y <= 260:
                        chosen = 1
                    elif 275 <= x <= 525 and 300 <= y <= 360:
                        chosen = 2
                    elif event.pressed:
                        chosen = 0

                # REJESTRACJA
                elif actual == 2:
                    if 275 <= x <= 525 and 500 <= y <= 560:
                        actual = 0
                        regerror = 0
                        logg.string = ""
                        pas.string = ""
                        password = ""
                    elif 275 <= x <= 525 and 400 <= y <= 460:
                        if rejestracja(session, logg.string, password):
                            actual = 0
                            regerror = 0
                            logg.string = ""
                            pas.string = ""
                            password = ""
                        else:
                            actual = 2
                            regerror = 1
                    elif 275 <= x <= 525 and 200 <= y <= 260:
                        chosen = 1
                    elif 275 <= x <= 525 and 300 <= y <= 360:
                        chosen = 2
                    elif event.pressed:
                        chosen = 0

                elif actual == 3:
                    if 275 <= x <= 525 and 500 <= y <= 560:
                        actual = 0

                # STRONA GŁÓWNA GRY
                elif actual == 4:
                    if option == 1 and 550 <= x <= 750 and 200 <= y <= 260:
                        option = 0
                        actual = 5
                        wyjscie_z_menu(session)
                        gra = nowa_gra(session)
                        if gra is None:
                            waiting = 1
                        else: waiting = 0
                        print("WAITING")
                        print(waiting)
                    elif 20 <= x <= 270 and 200 <= y <= 260:
                        option = 1
                    elif 20 <= x <= 270 and 280 <= y <= 340:
                        option = 2
                    elif 20 <= x <= 270 and 360 <= y <= 420:
                        option = 3
                    elif 20 <= x <= 270 and 440 <= y <= 500:
                        option = 4
                    elif 20 <= x <= 270 and 520 <= y <= 580:
                        wyjscie_z_menu(session)
                        wylogowywanie(session)
                        actual = 0
                        option = 0
                    else:
                        pass

                #GRA WŁAŚCIWA
                elif actual == 5:
                    if 20 <= x <= 200 and 20 <= y <= 80:
                        actual = 4
                        gra.abandon().result


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
                    gra.get_transformable_pawn().rotate_clockwise()
                elif actual == 5 and event.code == sf.Keyboard.LEFT:
                    gra.get_transformable_pawn().rotate_clockwise()
                    gra.get_transformable_pawn().rotate_clockwise()
                    gra.get_transformable_pawn().rotate_clockwise()


        if not window.is_open:
            break

        window.clear()
        window.draw(ground)
        if actual == 1 or actual == 2:
            if chosen == 1:
                login.color = sf.Color(255, 255, 255, 200)
                haslo.color = sf.Color(255, 255, 255, 100)
            elif chosen == 2:
                login.color = sf.Color(255, 255, 255, 100)
                haslo.color = sf.Color(255, 255, 255, 200)
            else:
                login.color = sf.Color(255, 255, 255, 100)
                haslo.color = sf.Color(255, 255, 255, 100)

            window.draw(login)
            window.draw(login_txt)
            window.draw(haslo)
            window.draw(haslo_txt)
            window.draw(menu)
            window.draw(menu_txt)
            window.draw(logg)
            window.draw(pas)

        if actual == 1:
            if logerror:
                window.draw(logerror_txt)
            window.draw(zaloguj)
            window.draw(zaloguj_txt)

        if actual == 2:
            if regerror:
                window.draw(regerror_txt)
            window.draw(rejestruj)
            window.draw(rejestruj_txt)

        if actual == 4:
            window.draw(game)
            window.draw(nowa)
            window.draw(nowa_txt)
            window.draw(ranking)
            window.draw(ranking_txt)
            window.draw(przyjaciele)
            window.draw(przyjaciele_txt)
            window.draw(zmiany)
            window.draw(zmiany_txt)
            window.draw(wyloguj)
            window.draw(wyloguj_txt)
            if option == 1:
                window.draw(box)
                heading = txt(300, 200, tek="Online Players", size=33, fo=font)
                window.draw(heading)
                random, random_txt = przycisk("Random player", 650, 230, 20, 200, lenx=200)
                window.draw(random)
                window.draw(random_txt)
                counter = 0
                for gamer in zalogowani(session):
                    player, player_txt = przycisk(gamer, 525, 295+50*counter, 20, 100, lenx=450, leny=40, fo=font2,
                                                  color=sf.Color.WHITE, style=sf.Text.REGULAR)
                    window.draw(player)
                    window.draw(player_txt)
                    counter += 1


        if actual == 5:
            if waiting == 1:
                window.draw(wait)
            else:
                window.draw(big_box)
                window.draw(big_box2)
                window.draw(finish)
                window.draw(finish_txt)

                KOL1 = sf.Color(64, 255, 128, 255)
                KOL1b = sf.Color(64, 255, 128, 150)
                KOL2 = sf.Color(64, 32, 192, 255)
                KOL2b = sf.Color(64, 32, 192, 150)

                play1 = txt(20, 80, tek="Player1", size=42, fo=font, color=KOL1)
                res1 = txt(20, 130, tek="42", size=42, fo=font, color=KOL1)
                play2 = txt(20, 500, tek="Player2", size=42, fo=font, color=KOL2)
                res2 = txt(20, 450, tek="69", size=42, fo=font, color=KOL2)

                fig_y = gra.get_transformable_pawn().height
                fig_x = gra.get_transformable_pawn().width

                list_fig = []
                czy_zielona = 1

                wym = 500/max(gra.width, gra.height)

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
                        if y < 50+(poz_y+1)*wym and y+(fig_y-1)*wym > 50+poz_y*wym and x < 250+(poz_x+1)*wym \
                                and x+(fig_x-1)*wym > 250+poz_x*wym \
                                and gra.get_transformable_pawn().get_pawn_point(floor((250-x)/wym +poz_x+1), floor((50-y)/wym +poz_y+1)) \
                                and y+(fig_y-1)*wym <= 50 + gra.height * wym and y >= 50 \
                                and x+(fig_x-1)*wym <= 250 + gra.width * wym and x >= 250:
                            if gra.get_field(poz_x, poz_y)[0] != 0:
                                czy_zielona = 0
                            list_fig.append((250+poz_x*(wym-1), 50+poz_y*(wym-1)))
                        elif gra.get_field(poz_x, poz_y)[0] == 0:
                            kwadrat.color = sf.Color(255,255,255,255)
                        elif gra.get_field(poz_x, poz_y)[0] == 1:
                            kwadrat.color = KOL1
                        elif gra.get_field(poz_x, poz_y)[0] == -1:
                            kwadrat.color = KOL1b
                        elif gra.get_field(poz_x, poz_y)[0] == 2:
                            kwadrat.color = KOL2
                        elif gra.get_field(poz_x, poz_y)[0] == -2:
                            kwadrat.color = KOL2b
                        elif gra.get_field(poz_x, poz_y)[0] == -3:
                            kwadrat.color = sf.Color(255, 255, 255, 0)

                        kwadrat.position = sf.Vector2(250+poz_x*(wym-1), 50+poz_y*(wym-1))
                        window.draw(kwadrat)
                        if gra.get_field(poz_x, poz_y)[1] < 0:
                            numerek = txt(250+poz_x*(wym-1)+wym/8, 50+poz_y*(wym-1), tek=str(gra.get_field(poz_x, poz_y)[1]), size=wym*3/5)
                        else:
                            numerek = txt(250+poz_x*(wym-1)+wym/5, 50+poz_y*(wym-1), tek=str(gra.get_field(poz_x, poz_y)[1]), size=wym*3/5)
                        if gra.get_field(poz_x, poz_y)[0] != -3:
                            window.draw(numerek)
                        poz_x += 1
                    poz_y += 1

                if gra.is_active_player():
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

        #Error 404
        if actual == 3:
            window.draw(game)
            window.draw(lazy)
            window.draw(menu)
            window.draw(menu_txt)

        if actual == 0:
            window.draw(game)
            window.draw(log)
            window.draw(log_txt)
            window.draw(konto)
            window.draw(konto_txt)
            window.draw(offline)
            window.draw(offline_txt)

        window.display()

if __name__ == "__main__":
    main()