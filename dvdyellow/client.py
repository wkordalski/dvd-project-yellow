import os
from dvdyellow.game import *
import sfml as sf

data_directory = 'data'
font = sf.Font.from_file(os.path.join(data_directory, "celtic.ttf"))
font2 = sf.Font.from_file(os.path.join(data_directory, "arial.ttf"))


# przycisk o wymiarach 250x60
def przycisk(napis, x, y, minus_y, jasnosc):
    pole = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "czerwony.JPG")))
    pole.texture_rectangle = sf.Rectangle((10, 10), (250, 60))
    pole.color = sf.Color(255, 255, 255, jasnosc)  # RGB, jasność
    pole.position = sf.Vector2(x-125, y-30)
    tekst = sf.Text(napis)
    tekst.font = font
    tekst.character_size = 30
    tekst.style = sf.Text.BOLD
    tekst.color = sf.Color.BLACK
    dl = len(napis)
    tekst.position = x-6.35*dl, y-minus_y
    return pole, tekst


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
    session.sign_out()


def zalogowani(session):
    return session.get_waiting_room().result.get_online_users().result


def main():
    
    w, h = sf.Vector2(800, 600)
    window = sf.RenderWindow(sf.VideoMode(w, h), "DVD Project Yellow Client")
    window.vertical_synchronization = True

    session = make_session('localhost').result
    ground = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "back.jpg")))

    GREY = sf.Color(195, 195, 195)


    #Pola klikalne na stronie startowej
    log, log_txt = przycisk("Log in", 400, 270, 20, 255)
    konto, konto_txt = przycisk("Sign up", 400, 370, 20, 255)
    offline, offline_txt = przycisk("Local game", 400, 470, 20, 255)

    #Pola do wpisania loginu i hasła
    login, login_txt = przycisk("Login", 400, 230, 70, 100)
    login_txt.color = GREY
    haslo, haslo_txt = przycisk("Password", 400, 330, 70, 100)
    haslo_txt.color = GREY

    #Pola klikalne na stronach logowania/rejestracji
    zaloguj, zaloguj_txt = przycisk("Log in", 400, 430, 20, 255)
    rejestruj, rejestruj_txt = przycisk("Sign up", 400, 430, 20, 255)
    menu, menu_txt = przycisk("Menu", 400, 530, 20, 255)
    
    #Pola klikalne na stronie głównej
    nowa, nowa_txt = przycisk("New game", 145, 230, 20, 255)
    ranking, ranking_txt = przycisk("Ranking", 145, 310, 20, 255) 
    przyjaciele, przyjaciele_txt = przycisk("Friends", 145, 390, 20, 255)
    zmiany, zmiany_txt = przycisk("Account settings", 145, 470, 20, 255)
    wyloguj, wyloguj_txt = przycisk("Log out", 145, 550, 20, 255)

    #Duża ramka na stronie głównej
    box = sf.Sprite(sf.Texture.from_file(os.path.join(data_directory, "czerwony.JPG")))
    box.texture_rectangle = sf.Rectangle((10, 10), (450, 380))
    box.color = sf.Color(255, 255, 255, 100)  # RGB, jasność
    box.position = sf.Vector2(300, 200)

    #Napis na grze lokalnej
    lazy = sf.Text("Error 404 - this page isn't available now, \nbecause programmers are too lazy. Sorry")
    lazy.font = font
    lazy.character_size = 35
    lazy.color = GREY
    lazy.position = 160, 200


    #Nazwa gry
    game = sf.Text("Nazwa gry")
    game.font = font
    game.character_size = 100
    game.color = GREY
    game.position = 210, 50


    #Błędy
    logerror_txt = txt(140, 50, color = GREY, size = 35, fo = font)
    logerror_txt.string = "Sorry, your login or password is incorrect.\n                 Please try again"
    logerror = 0
    regerror_txt = txt(223, 50, color=GREY, size=35, fo=font)
    regerror_txt.string = "This login is already used.\n       Please try again"
    regerror = 0


    logg = txt(275, 200)
    pas = txt(275, 300)
    password = ""

    position = sf.Mouse.get_position()
    print(position)

    chosen = 0 #1-login, 2-password
    actual = 0 #0-page0, 1-logowanie, 2-rejestracja, 3-gra lokalna, 4-menu główne
    option = 0 #1-new game, 2- ranking, 3-friends, 4-settings
    
    x, y = 0, 0


    while window.is_open:
        for event in window.events:
            if event == sf.CloseEvent:
                window.close()
            if event == sf.MouseMoveEvent:
                x, y = event.position

            #ZABAWY MYSZKĄ
            if event == sf.MouseButtonEvent and event.pressed:
                #STRONA STARTOWA
                if actual == 0:
                    chosen = 0
                    if 275 <= x <= 525 and 240 <= y <= 300:
                        actual = 1
                    if 275 <= x <= 525 and 340 <= y <= 400:
                        actual = 2
                    if 275 <= x <= 525 and 440 <= y <= 500:
                        actual = 3
                        

                #LOGOWANIE
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


                #REJESTRACJA
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
                    
                
                #STRONA GŁÓWNA GRY  
                elif actual == 4:
                    if 20 <= x <= 270 and 200 <= y <= 260:
                        option = 1
                    elif 20 <= x <= 270 and 280 <= y <= 340:
                        option = 2
                    elif 20 <= x <= 270 and 360 <= y <= 420:
                        option = 3
                    elif 20 <= x <= 270 and 440 <= y <= 500:
                        option = 4
                    elif 20 <= x <= 270 and 520 <= y <= 580:
                        wylogowywanie(session)
                        actual = 0
                        option = 0
                    else:
                        pass


            #ZABAWY KLAWIATURĄ
            if event == sf.TextEvent:
                if chosen == 1:
                    if len(logg.string) < 9 and str(event.unicode) != "8":
                        logg.string += chr(event.unicode)
                    elif str(event.unicode) == "8":
                        logg.string = logg.string[0:-1]
                elif chosen == 2:
                    if len(pas.string) < 22 and str(event.unicode) != "8":
                        pas.string += "*"
                        password += chr(event.unicode)
                    elif str(event.unicode) == "8":
                        pas.string = pas.string[0:-1]
                        password = password[0:-1]



        window.clear()
        window.draw(ground)
        if actual == 1 or actual == 2:
            if chosen == 1:
                login.color = sf.Color(255,255,255,200)
                haslo.color = sf.Color(255,255,255,100)
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
                heading = txt(300, 200, tek="Online Players", size = 33)
                window.draw(heading)
                counter = 0
                for gamer in zalogowani(session):
                    player = txt(300,250+31*counter, tek=gamer, color = sf.Color.RED, size = 27)
                    window.draw(player)
                    counter+=1

            
        if actual == 3:
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
