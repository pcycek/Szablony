# Instrukcja obsługi Git dla projektu Szablony

## 1. Jak wysłać nowe zmiany na GitHub

Gdy wprowadzisz zmiany w kodzie (np. dodasz nową funkcję lub poprawisz błąd), wykonaj następujące kroki w terminalu:

1.  **Sprawdź status plików** (opcjonalnie, ale zalecane):
    ```bash
    git status
    ```
    To pokaże Ci, które pliki zostały zmienione (na czerwono).

2.  **Dodaj zmiany do "poczekalni" (stage)**:
    ```bash
    git add .
    ```
    Kropka `.` oznacza "wszystkie pliki". Jeśli chcesz dodać tylko konkretny plik, wpisz jego nazwę zamiast kropki, np. `git add main.py`.

3.  **Zatwierdź zmiany (zrób commit)**:
    ```bash
    git commit -m "Opis tego co zrobiłem"
    ```
    W cudzysłowie wpisz krótki, ale jasny opis zmian, np. "Dodanie funkcji druku" lub "Poprawa błędu w szablonach".

4.  **Wyślij na GitHub**:
    ```bash
    git push
    ```
    To polecenie przesyła Twoje zatwierdzone zmiany na serwer GitHub.

---

## 2. Jak cofnąć zmiany

Sposób cofania zależy od tego, na jakim etapie jesteś.

### A. Zmiany są tylko na Twoim dysku (nie zrobiłeś jeszcze `git commit`)

Jeśli edytowałeś plik, ale zmiany Ci się nie podobają i chcesz wrócić do wersji ostatnio zapisanej w Git:

*   **Dla jednego pliku:**
    ```bash
    git restore nazwa_pliku.py
    ```
*   **Dla wszystkich plików (UWAGA: to skasuje całą Twoją niezapisaną pracę!):**
    ```bash
    git restore .
    ```

### B. Zrobiłeś już `git commit`, ale nie wysłałeś jeszcze (`git push`)

Jeśli zatwierdziłeś zmiany lokalnie, ale chcesz je cofnąć:

*   **Cofnij commit, ale zostaw zmiany w plikach** (żeby móc je poprawić):
    ```bash
    git reset --soft HEAD~1
    ```
*   **Cofnij commit i usuń zmiany całkowicie** (powrót do stanu sprzed commita):
    ```bash
    git reset --hard HEAD~1
    ```

### C. Wysłałeś już zmiany na GitHub (`git push`)

Jeśli zmiany są już publiczne, najlepiej "nadpisać" je nowym commitem, który cofa zmiany (tzw. revert), zamiast usuwać historię.

1.  Znajdź identyfikator commita, który chcesz cofnąć (wpisz `git log` i skopiuj ciąg znaków np. `a1b2c3d`).
2.  Wpisz:
    ```bash
    git revert a1b2c3d
    ```
    To stworzy *nowy* commit, który jest odwrotnością tego błędnego. Potem zrób `git push`.
