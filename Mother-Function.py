import os


if __name__ == "__main__":
    counter = 0
    key1 = "aMbRcPdZeMfAgDhEiMjEkAlDmDnToHpIqSr:s(t"
    key_match = None
    while counter < 2:
        os.system("python3 main.py")
        if os.path.exists("exit_key.txt"):
            with open("exit_key.txt", "r") as file:
                key_match = file.read()
            if key_match == key1:
                os.remove("exit_key.txt")
                print("breaking...")
                break
        else:
            print("Continue")
            counter += 1




