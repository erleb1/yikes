import random

def get_common_hebrew_words():
    """Replace with actual list of common Hebrew words"""
    return ["אדם", "בית", "שמש", "עץ", "דרך", "אהבה", "יום", "חלום", "ילד"] 

def display_board(guesses, word_length):
    for guess in guesses:
        for i, letter in enumerate(guess):
            color = "⬜"  # Default: White (not guessed)
            if letter in answer:
                color = "🟨"  # Yellow (correct but wrong position)
                if letter == answer[i]:
                    color = "🟩"  # Green (correct letter and position)
            print(color, end="")
        print()  # Move to the next line

def main():
    word_length = 5  # Standard Wordle length
    max_attempts = 6  # Standard Wordle attempts
    common_words = get_common_hebrew_words()
    answer = random.choice(common_words)

    print("\nברוכים הבאים לוורדל העברי! 🇮🇱")
    print("נסו לנחש את המילה בעברית בת חמש אותיות. יש לכם", max_attempts, "נסיונות.")

    guesses = []
    while len(guesses) < max_attempts:
        guess = input("ניחוש: ").strip()
        if len(guess) != word_length or not guess.isalpha():
            print("אנא הזינו מילה בת", word_length, "אותיות.")
            continue

        guesses.append(guess)
        display_board(guesses, word_length)

        if guess == answer:
            print("כל הכבוד! ניחשתם נכון! 🎉")
            break
    else:
        print("לא נורא, המילה הייתה:", answer)

if __name__ == "__main__":
    main()

