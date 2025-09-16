# Copyright 2024 Artificial Intelligence Labs, SL

import re
from typing import Optional


class SpanishTaxValidator:
    """
    Validates Spanish tax identification numbers (NIF, CIF, NIE).
    """

    def __init__(self):
        # Spanish NIF/NIE control letters
        self.nif_letters = "TRWAGMYFPDXBNJZSQVHLCKE"
        self.nie_letters = "XYZ"

        # CIF organization type letters and their control algorithms
        self.cif_types = {
            'A': 'number',    # Sociedades anónimas
            'B': 'number',    # Sociedades de responsabilidad limitada
            'C': 'number',    # Sociedades colectivas
            'D': 'number',    # Sociedades comanditarias
            'E': 'number',    # Comunidades de bienes
            'F': 'number',    # Sociedades cooperativas
            'G': 'number',    # Asociaciones
            'H': 'number',    # Comunidades de propietarios
            'J': 'number',    # Sociedades civiles
            'N': 'letter',    # Entidades extranjeras
            'P': 'letter',    # Corporaciones locales
            'Q': 'letter',    # Organismos públicos
            'R': 'letter',    # Congregaciones religiosas
            'S': 'letter',    # Órganos de la Administración del Estado
            'U': 'letter',    # Uniones temporales de empresas
            'V': 'letter',    # Otros tipos no definidos
            'W': 'letter',    # Establecimientos permanentes
        }

    def validate_cif_nif(self, tax_id: str) -> bool:
        """
        Validate Spanish tax identification numbers.

        Args:
            tax_id: Tax identification string

        Returns:
            True if valid, False otherwise
        """
        if not tax_id:
            return False

        # Clean the input
        tax_id = tax_id.upper().strip().replace(' ', '').replace('-', '')

        # Try different validation methods
        return (self._validate_nif(tax_id) or
                self._validate_nie(tax_id) or
                self._validate_cif(tax_id))

    def _validate_nif(self, nif: str) -> bool:
        """Validate Spanish NIF (Número de Identificación Fiscal)."""
        if not re.match(r'^\d{8}[A-Z]$', nif):
            return False

        number = int(nif[:8])
        letter = nif[8]
        expected_letter = self.nif_letters[number % 23]

        return letter == expected_letter

    def _validate_nie(self, nie: str) -> bool:
        """Validate Spanish NIE (Número de Identidad de Extranjero)."""
        if not re.match(r'^[XYZ]\d{7}[A-Z]$', nie):
            return False

        # Convert first letter to number
        first_letter = nie[0]
        if first_letter == 'X':
            number_str = '0' + nie[1:8]
        elif first_letter == 'Y':
            number_str = '1' + nie[1:8]
        elif first_letter == 'Z':
            number_str = '2' + nie[1:8]
        else:
            return False

        number = int(number_str)
        letter = nie[8]
        expected_letter = self.nif_letters[number % 23]

        return letter == expected_letter

    def _validate_cif(self, cif: str) -> bool:
        """Validate Spanish CIF (Código de Identificación Fiscal)."""
        if not re.match(r'^[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]$', cif):
            return False

        org_type = cif[0]
        number_part = cif[1:8]
        control_char = cif[8]

        if org_type not in self.cif_types:
            return False

        # Calculate control digit/letter
        control_type = self.cif_types[org_type]

        # Sum calculation for CIF
        odd_sum = sum(int(number_part[i]) for i in range(0, 7, 2))

        even_sum = 0
        for i in range(1, 7, 2):
            double = int(number_part[i]) * 2
            even_sum += double // 10 + double % 10

        total_sum = odd_sum + even_sum
        control_digit = (10 - (total_sum % 10)) % 10

        if control_type == 'number':
            return control_char == str(control_digit)
        else:  # control_type == 'letter'
            control_letters = "JABCDEFGHI"
            expected_letter = control_letters[control_digit]
            return control_char == expected_letter or control_char == str(control_digit)

    def get_tax_id_type(self, tax_id: str) -> Optional[str]:
        """
        Determine the type of Spanish tax ID.

        Returns:
            'NIF', 'NIE', 'CIF', or None if invalid
        """
        if not tax_id:
            return None

        tax_id = tax_id.upper().strip()

        if self._validate_nif(tax_id):
            return 'NIF'
        elif self._validate_nie(tax_id):
            return 'NIE'
        elif self._validate_cif(tax_id):
            return 'CIF'
        else:
            return None