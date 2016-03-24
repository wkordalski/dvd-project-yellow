import sfml as sf

def main():
	w, h = sf.Vector2(800, 600)
	window = sf.RenderWindow(sf.VideoMode(w, h), "DVD Project Yellow Client")
	window.vertical_synchronization = True
	
	while window.is_open:
		for event in window.events:
			if event == sf.CloseEvent:
		    		window.close()
		window.display()


if __name__ == "__main__":
	main()
