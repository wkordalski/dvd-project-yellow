import sfml as sf


font = sf.Font.from_file("celtic.ttf")
font2 = sf.Font.from_file("arial.ttf")

# przycisk o wymiarach 250x60
def przycisk(napis, x, y, minus_y, jasnosc):
    pole = sf.Sprite(sf.Texture.from_file("czerwony.JPG"))
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

def txt(x, y):
    tekst = sf.Text("")
    tekst.font = font2
    tekst.character_size = 25
    tekst.color = sf.Color.BLUE
    tekst.position = x+10, y+10
    return tekst


def main():
    w, h = sf.Vector2(800, 600)
    window = sf.RenderWindow(sf.VideoMode(w, h), "DVD Project Yellow Client")
    window.vertical_synchronization = True

    ground = sf.Sprite(sf.Texture.from_file("back.jpg"))

    #Pola klikalne na stronie startowej
    log, log_txt = przycisk("Log in", 400, 330, 20, 255)
    konto, konto_txt = przycisk("Sign up", 400, 430, 20, 255)

    #Pola do wpisania loginu i hasła
    login, login_txt = przycisk("Login", 400, 230, 70, 100)
    haslo, haslo_txt = przycisk("Password", 400, 330, 70, 100)

    #Pola klikalne na logowaniu/rejestracji
    zaloguj, zaloguj_txt = przycisk("Log in", 400, 430, 20, 255)
    rejestruj, rejestruj_txt = przycisk("Sign up", 400, 430, 20, 255)
    menu, menu_txt = przycisk("Menu", 400, 530, 20, 255)


    logg = txt(275, 200)
    pas = txt(275, 300)
    password = ""

    position = sf.Mouse.get_position()
    print(position)

    logowanie = 0
    nowekonto = 0
    start = 1
    gra = 0
    chosen = 0 #1-login, 2-haslo

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
                if start == 1:
                    chosen = 0
                    logg.string = ""
                    pas.string = ""
                    password = ""
                    if 275 <= x <= 525 and 300 <= y <= 360:
                        logowanie = 1
                        start = 0
                    if 275 <= x <= 525 and 400 <= y <= 460:
                        nowekonto = 1
                        start = 0

                #LOGOWANIE
                elif logowanie == 1:
                    if 275 <= x <= 525 and 500 <= y <= 560:
                        logowanie = 0
                        start = 1
                    elif 275 <= x <= 525 and 400 <= y <= 460:
                        logowanie = 0
                        gra = 1
                    elif 275 <= x <= 525 and 200 <= y <= 260:
                        chosen = 1
                        #login.color = sf.Color(255, 255, 255, 30)
                    elif 275 <= x <= 525 and 300 <= y <= 360:
                        chosen = 2
                        #haslo.color = sf.Color(255, 255, 255, 30)
                    elif event.pressed:
                        chosen = 0


                #REJESTRACJA
                elif nowekonto == 1:
                    if 275 <= x <= 525 and 500 <= y <= 560:
                        nowekonto = 0
                        start = 1
                    elif 275 <= x <= 525 and 400 <= y <= 460:
                        nowekonto = 0
                        gra = 1
                    elif 275 <= x <= 525 and 200 <= y <= 260:
                        chosen = 1
                    elif 275 <= x <= 525 and 300 <= y <= 360:
                        chosen = 2
                    elif event.pressed:
                        chosen = 0

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
                    elif str(event.unicode) == 8:
                        pas.string = pas.string[0:-1]
                        password = password[0:-1]


        window.clear()
        window.draw(ground)
        if logowanie == 1 or nowekonto == 1:
            window.draw(login)
            window.draw(login_txt)
            window.draw(haslo)
            window.draw(haslo_txt)
            window.draw(menu)
            window.draw(menu_txt)
            window.draw(logg)
            window.draw(pas)

        if logowanie == 1:
            window.draw(zaloguj)
            window.draw(zaloguj_txt)

        elif nowekonto == 1:
            window.draw(rejestruj)
            window.draw(rejestruj_txt)

        elif gra == 1:
            pass
        else:
            window.draw(log)
            window.draw(log_txt)
            window.draw(konto)
            window.draw(konto_txt)

        window.display()


if __name__ == "__main__":
    main()
