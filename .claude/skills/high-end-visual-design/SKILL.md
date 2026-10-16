---
name: high-end-visual-design
description: Referencias de acabado premium para las pantallas de este repo: espaciado, superficies, sombra, jerarquía tipográfica, micro-interacciones y estados vacíos que invitan a actuar. Úsala junto a frontend-design al construir o rediseñar una pantalla, cuando lo que falta no es estructura sino oficio visual.
---

# Acabado visual (backmanagercne)

Reconstruida el 2026-09-16 con las convenciones reales del repo. **Nunca degradados, nunca
glassmorphism, nunca `backdrop-filter`** en la plataforma autenticada: la jerarquía se expresa con
superficies sólidas, borde y sombra corta.

## Espaciado: una escala, no números al azar

Usa la escala de Bootstrap (`.25 / .5 / 1 / 1.5 / 3 rem` → `g-1 g-2 g-3 g-4 g-5`) y elige **dos o
tres** valores para toda la pantalla. El error más común no es elegir mal el valor: es usar seis
valores distintos. Dentro de una tarjeta, el aire entre bloques relacionados (`.5rem`) tiene que ser
claramente menor que el aire entre bloques distintos (`1rem`): eso es lo que agrupa sin dibujar cajas.

## Superficies y profundidad

Tres niveles alcanzan: fondo de página, tarjeta (`#fff` con borde `1px #dfe5ea`) y celda interior
(`#fbfcfd`). La profundidad se sugiere con el borde, no con la sombra. La sombra es para el hover y
para lo que flota (modal, menú): corta y de baja opacidad, `0 6px 18px rgba(22, 50, 79, .08)`.
Una sombra difusa y grande en una tarjeta estática es el sello del diseño amateur.

## Jerarquía tipográfica

Tres niveles por tarjeta, no cinco: **nombre** (`1.05rem`, 700, color fuerte), **dato** (`.9rem`,
600, tabular para cifras), **etiqueta y apoyo** (`.7rem` mayúsculas con tracking, o `.8rem` normal
en color de apoyo). El peso separa mejor que el tamaño: antes de agrandar, prueba subir el peso o
bajar el color del texto secundario.

## Color con significado

El acento se reserva para lo accionable y lo actual. Si todo es azul, nada es azul. Los estados se
leen antes que el texto: verde vive, ámbar espera, gris duerme, rojo destruye. Un borde superior de
3px que cambia de color según el estado hace escaneable una grilla de 30 tarjetas sin leer una
palabra — y es más barato que cualquier ilustración.

## Micro-interacciones

Solo donde confirman algo: `transition: box-shadow .15s ease` en el hover de la tarjeta, el botón
que cambia a «Copiado» un segundo, la barra que se mueve con `transition: width .6s ease` en vez de
saltar. Nada que se mueva solo y para siempre. Respeta `prefers-reduced-motion: reduce`.

## Estados vacíos que invitan

Un estado vacío es una oportunidad de enseñar, no un cartel de error. Tres partes: qué es esta
pantalla en una frase, los pasos reales del flujo **vigente** numerados, y el botón que arranca el
primero. Si el flujo cambió y el estado vacío sigue contando el anterior, la pantalla miente en el
único momento en que el usuario está prestando atención.

## Densidad de herramienta

Esto es un panel de trabajo: el administrador mira 30 aulas, no una portada. Prefiere la tabla o la
tarjeta compacta al hero gigante, muestra el número antes que la palabra, y no obligues a abrir un
modal para ver un dato que cabe en la fila.

## Detalles que separan lo correcto de lo bueno

- Cifras alineadas a la derecha y tabulares; nada baila al actualizarse.
- Texto largo con `text-truncate` + `title`, o `overflow-wrap: anywhere` en URLs.
- El foco visible se diseña, no se borra: `box-shadow: 0 0 0 .2rem rgba(28, 63, 134, .25)`.
- Iconos con significado constante en toda la app; si el icono no agrega, sobra.
- Copy en español, voz activa, sin jerga de sistema: «Esperando aprobación», no «Estado: 0».
