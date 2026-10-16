"""Carga Ecuador con sus 24 provincias y todos sus cantones (ciudades) en
`area_geografica.Pais` / `Provincia` / `Ciudad`.

El registro público (/register/) arma sus selects de provincia y ciudad desde estas tablas; sin la
data de Ecuador cargada, esos combos salen vacíos. `seed_paises.py` solo cargaba la capital de cada
país — este script completa Ecuador entero.

Idempotente: `get_or_create` por nombre en MAYÚSCULAS (así lo normaliza `Pais.save()` /
`Provincia.save()` / `Ciudad.save()`), se puede correr varias veces sin duplicar. `timezone` usa un
valor válido de `core.constantes.TIMEZONE_CHOICES` (hay un CheckConstraint en BD que lo exige).

Uso (desde la raíz del repo):
    python scripts/seed_ecuador_geo.py
    python scripts/seed_ecuador_geo.py --dry-run
"""
import argparse
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.db import transaction


PAIS = {'codigo': 'EC', 'nombre': 'Ecuador', 'codigotelefono': '+593',
        'codigoidioma': 'es', 'timezone': 'America/Guayaquil'}

# Provincia -> cantones (el primero es la capital provincial). Fuente: división política del Ecuador.
PROVINCIAS = {
    'Azuay': ['Cuenca', 'Girón', 'Gualaceo', 'Nabón', 'Paute', 'Pucará', 'San Fernando',
              'Santa Isabel', 'Sígsig', 'Oña', 'Chordeleg', 'El Pan', 'Sevilla de Oro',
              'Guachapala', 'Camilo Ponce Enríquez'],
    'Bolívar': ['Guaranda', 'Chillanes', 'Chimbo', 'Echeandía', 'San Miguel', 'Caluma', 'Las Naves'],
    'Cañar': ['Azogues', 'Biblián', 'Cañar', 'La Troncal', 'El Tambo', 'Déleg', 'Suscal'],
    'Carchi': ['Tulcán', 'Bolívar', 'Espejo', 'Mira', 'Montúfar', 'San Pedro de Huaca'],
    'Chimborazo': ['Riobamba', 'Alausí', 'Colta', 'Chambo', 'Chunchi', 'Guamote', 'Guano',
                   'Pallatanga', 'Penipe', 'Cumandá'],
    'Cotopaxi': ['Latacunga', 'La Maná', 'Pangua', 'Pujilí', 'Salcedo', 'Saquisilí', 'Sigchos'],
    'El Oro': ['Machala', 'Arenillas', 'Atahualpa', 'Balsas', 'Chilla', 'El Guabo', 'Huaquillas',
               'Marcabelí', 'Pasaje', 'Piñas', 'Portovelo', 'Santa Rosa', 'Zaruma', 'Las Lajas'],
    'Esmeraldas': ['Esmeraldas', 'Eloy Alfaro', 'Muisne', 'Quinindé', 'San Lorenzo', 'Atacames',
                   'Rioverde'],
    'Galápagos': ['San Cristóbal', 'Isabela', 'Santa Cruz'],
    'Guayas': ['Guayaquil', 'Alfredo Baquerizo Moreno', 'Balao', 'Balzar', 'Colimes', 'Daule',
               'Durán', 'El Empalme', 'El Triunfo', 'Milagro', 'Naranjal', 'Naranjito', 'Palestina',
               'Pedro Carbo', 'Samborondón', 'Santa Lucía', 'Salitre', 'San Jacinto de Yaguachi',
               'Playas', 'Simón Bolívar', 'Coronel Marcelino Maridueña', 'Lomas de Sargentillo',
               'Nobol', 'General Antonio Elizalde', 'Isidro Ayora'],
    'Imbabura': ['Ibarra', 'Antonio Ante', 'Cotacachi', 'Otavalo', 'Pimampiro',
                 'San Miguel de Urcuquí'],
    'Loja': ['Loja', 'Calvas', 'Catamayo', 'Celica', 'Chaguarpamba', 'Espíndola', 'Gonzanamá',
             'Macará', 'Paltas', 'Puyango', 'Saraguro', 'Sozoranga', 'Zapotillo', 'Pindal',
             'Quilanga', 'Olmedo'],
    'Los Ríos': ['Babahoyo', 'Baba', 'Montalvo', 'Puebloviejo', 'Quevedo', 'Urdaneta', 'Ventanas',
                 'Vinces', 'Palenque', 'Buena Fe', 'Valencia', 'Mocache', 'Quinsaloma'],
    'Manabí': ['Portoviejo', 'Bolívar', 'Chone', 'El Carmen', 'Flavio Alfaro', 'Jipijapa', 'Junín',
               'Manta', 'Montecristi', 'Paján', 'Pichincha', 'Rocafuerte', 'Santa Ana', 'Sucre',
               'Tosagua', '24 de Mayo', 'Pedernales', 'Olmedo', 'Puerto López', 'Jama', 'Jaramijó',
               'San Vicente'],
    'Morona Santiago': ['Macas', 'Gualaquiza', 'Limón Indanza', 'Palora', 'Santiago', 'Sucúa',
                        'Huamboya', 'San Juan Bosco', 'Taisha', 'Logroño', 'Pablo Sexto', 'Tiwintza'],
    'Napo': ['Tena', 'Archidona', 'El Chaco', 'Quijos', 'Carlos Julio Arosemena Tola'],
    'Orellana': ['Francisco de Orellana', 'Aguarico', 'La Joya de los Sachas', 'Loreto'],
    'Pastaza': ['Puyo', 'Mera', 'Santa Clara', 'Arajuno'],
    'Pichincha': ['Quito', 'Cayambe', 'Mejía', 'Pedro Moncayo', 'Rumiñahui',
                  'San Miguel de los Bancos', 'Pedro Vicente Maldonado', 'Puerto Quito'],
    'Santa Elena': ['Santa Elena', 'La Libertad', 'Salinas'],
    'Santo Domingo de los Tsáchilas': ['Santo Domingo', 'La Concordia'],
    'Sucumbíos': ['Nueva Loja', 'Gonzalo Pizarro', 'Putumayo', 'Shushufindi', 'Sucumbíos',
                  'Cascales', 'Cuyabeno'],
    'Tungurahua': ['Ambato', 'Baños de Agua Santa', 'Cevallos', 'Mocha', 'Patate', 'Quero',
                   'San Pedro de Pelileo', 'Santiago de Píllaro', 'Tisaleo'],
    'Zamora Chinchipe': ['Zamora', 'Chinchipe', 'Nangaritza', 'Yacuambi', 'Yantzaza', 'El Pangui',
                         'Centinela del Cóndor', 'Palanda', 'Paquisha'],
}


def log(msg):
    print(msg)


def run(dry_run):
    from area_geografica.models import Pais, Provincia, Ciudad

    total_prov = len(PROVINCIAS)
    total_ciud = sum(len(c) for c in PROVINCIAS.values())
    log(f'Sembrando Ecuador: {total_prov} provincias y {total_ciud} ciudades (cantones)...')

    if dry_run:
        log('DRY RUN -- no se escribe nada.')
        for prov, cantones in PROVINCIAS.items():
            log(f'  {prov}: {len(cantones)} cantones')
        return

    prov_nuevas = ciud_nuevas = 0
    with transaction.atomic():
        pais, _ = Pais.objects.get_or_create(
            nombre=PAIS['nombre'].upper(),
            defaults={
                'codigo': PAIS['codigo'],
                'codigotelefono': PAIS['codigotelefono'],
                'codigoidioma': PAIS['codigoidioma'],
                'timezone': PAIS['timezone'],
            },
        )
        for prov_nombre, cantones in PROVINCIAS.items():
            provincia, creada = Provincia.objects.get_or_create(
                nombre=prov_nombre.upper(), pais=pais,
            )
            if creada:
                prov_nuevas += 1
            for canton in cantones:
                _, ciud_creada = Ciudad.objects.get_or_create(
                    nombre=canton.upper(), provincia=provincia,
                )
                if ciud_creada:
                    ciud_nuevas += 1

    log(f'Listo. {prov_nuevas} provincias y {ciud_nuevas} ciudades nuevas '
        f'(el resto ya existía).')


def main():
    parser = argparse.ArgumentParser(description='Carga Ecuador con sus provincias y cantones.')
    parser.add_argument('--dry-run', action='store_true', help='No escribe cambios, solo reporta.')
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
