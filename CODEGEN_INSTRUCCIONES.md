# Capturar selectores de login (una sola vez)

1. Instala dependencias y navegadores de Playwright:
   ```
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Lanza el grabador apuntando al login de Renta 4:
   ```
   playwright codegen https://www.r4.com/login
   ```
   Esto abre dos ventanas: el navegador y el "Playwright Inspector" con el código generado en vivo.

3. En el navegador que se abre:
   - Escribe tu usuario en el campo correspondiente.
   - Escribe tu contraseña.
   - Haz click en el botón de acceder/entrar.
   - Espera a que cargue el área privada (dashboard).

4. En la ventana del Inspector verás código Python generado automáticamente, algo como:
   ```python
   page.fill("#usuario", "...")
   page.fill("#password", "...")
   page.click("button[type='submit']")
   ```
   (Los nombres reales de los selectores pueden variar.)

5. Copia esas 3-4 líneas (con los selectores, SIN tus credenciales reales) y pégamelas para que
   rellene `SELECTORS` en `src/renta4_scraper.py`.

6. También dime qué texto/elemento aparece SOLO cuando ya has iniciado sesión (ej. tu nombre,
   un botón "Cerrar sesión", el menú de cartera) — eso lo uso como `logged_in_marker` para
   confirmar que el login funcionó.

Cierra el navegador del grabador cuando termines, no hace falta guardar nada más ahí.
