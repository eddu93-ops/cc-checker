#!/usr/bin/env python3
import requests
import json
import random
import time
import os
import sqlite3
from datetime import datetime
from colorama import Fore, Style, init

# Inicializar colorama
init(autoreset=True)

class SecureCCChecker:
    def __init__(self):
        self.sk = ""
        self.sk_type = ""
        self.sk_status = ""  # 'live', 'dead', 'unknown'
        self.generated_cards = []
        self.valid_cards = []
        self.bins = []
        self.session_validations = 0
        self.load_bins()
        
    def load_bins(self):
        self.bins = [
            "411111", "424242", "453201", "491748", "455673", "402400", "448562",
            "555555", "510510", "520082", "542523", "550692", "530125",
            "400005", "511151", "522222", "533333", "544444",
            "453202", "450903", "462294", "403000", "410039",
            "516320", "516345", "527458", "535231", "543111",
            "453957", "471604", "402944", "448430", "455676",
            "516292", "516293", "516294", "542418", "542419"
        ]
    
    def validate_stripe_key(self, sk):
        """Validar si el SK está LIVE o DEAD"""
        try:
            headers = {
                'Authorization': f'Bearer {sk}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            # Intentar hacer una operación simple
            response = requests.get(
                'https://api.stripe.com/v1/balance',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return 'live', "✅ SK ACTIVO - Clave funcionando correctamente"
            elif response.status_code == 401:
                return 'dead', "❌ SK INVALIDO - Clave rechazada por Stripe"
            else:
                return 'unknown', f"⚠️ SK CON PROBLEMAS - Código: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return 'unknown', "🌐 ERROR DE CONEXIÓN - Verifica tu internet"
        except requests.exceptions.Timeout:
            return 'unknown', "⏰ TIMEOUT - Servidor no responde"
        except Exception as e:
            return 'unknown', f"❓ ERROR DESCONOCIDO: {str(e)}"
    
    def set_stripe_key(self):
        print(f"\n{Fore.CYAN}=== CONFIGURAR STRIPE SECRET KEY ===")
        sk = input("Ingresa tu Stripe Secret Key: ").strip()
        
        # Validar formato básico
        if not sk.startswith(('sk_test_', 'sk_live_')):
            print(f"{Fore.RED}✗ Formato de SK inválido")
            return False
        
        print(f"{Fore.YELLOW}🔍 Validando SK con Stripe...")
        
        # Validar el SK con Stripe
        sk_status, message = self.validate_stripe_key(sk)
        
        # Mostrar resultado de validación
        if sk_status == 'live':
            status_color = Fore.GREEN
            status_icon = "✅"
        elif sk_status == 'dead':
            status_color = Fore.RED  
            status_icon = "❌"
        else:
            status_color = Fore.YELLOW
            status_icon = "⚠️"
        
        print(f"{status_color}{status_icon} {message}")
        
        # Configurar según tipo de SK
        if sk.startswith('sk_test_'):
            self.sk = sk
            self.sk_type = 'test'
            self.sk_status = sk_status
            self.session_validations = 0
            
            if sk_status == 'live':
                print(f"{Fore.GREEN}🎯 SK de TEST configurado - Listo para validaciones")
            else:
                print(f"{Fore.YELLOW}⚠️  SK de TEST con problemas - Puede fallar")
            return True
            
        elif sk.startswith('sk_live_'):
            # Mostrar advertencias severas para LIVE
            if not self.show_live_warning():
                return False
                
            self.sk = sk
            self.sk_type = 'live'
            self.sk_status = sk_status
            self.session_validations = 0
            
            if sk_status == 'live':
                print(f"{Fore.GREEN}🎯 SK de LIVE configurado - Validaciones REALES")
                print(f"{Fore.RED}🚨 MÁXIMA PRECAUCIÓN - Estás usando clave REAL")
            elif sk_status == 'dead':
                print(f"{Fore.RED}❌ SK LIVE INVALIDO - No podrás hacer validaciones")
            else:
                print(f"{Fore.YELLOW}⚠️  SK LIVE CON PROBLEMAS - Puede fallar")
            return True
        
        return False
    
    def show_live_warning(self):
        """Mostrar advertencias severas para SK_LIVE"""
        print(f"\n{Fore.RED}╔{'═' * 70}╗")
        print(f"{Fore.RED}║{' ' * 70}║")
        print(f"{Fore.RED}║{Fore.YELLOW}              🚨 ADVERTENCIA - MODO LIVE ACTIVADO 🚨             {Fore.RED}║")
        print(f"{Fore.RED}║{' ' * 70}║")
        print(f"{Fore.RED}║{Fore.WHITE} • Estás usando una clave REAL de Stripe                      {Fore.RED}║")
        print(f"{Fore.RED}║{Fore.WHITE} • Las validaciones son con bancos REALES                     {Fore.RED}║")
        print(f"{Fore.RED}║{Fore.WHITE} • Stripe puede detectar y SUSPENDER tu cuenta                {Fore.RED}║")
        print(f"{Fore.RED}║{Fore.WHITE} • Límite de seguridad: 15 tarjetas por sesión                {Fore.RED}║")
        print(f"{Fore.RED}║{Fore.WHITE} • SOLO USO EDUCATIVO - RESPONSABILIDAD TOTAL                 {Fore.RED}║")
        print(f"{Fore.RED}║{' ' * 70}║")
        print(f"{Fore.RED}╚{'═' * 70}╝")
        
        confirm = input(f"\n{Fore.RED}¿Confirmas que entiendes los riesgos? (escribe 'SI' en mayúsculas): ")
        return confirm == 'SI'
    
    def generate_from_partial(self, partial_number):
        """Generar tarjeta desde número parcial con X"""
        number = ""
        for char in partial_number:
            if char.upper() == 'X':
                number += str(random.randint(0, 9))
            else:
                number += char
        
        while len(number) < 15:
            number += str(random.randint(0, 9))
        
        return self.luhn_complete(number)
    
    def generate_cc(self, input_data=None, month=None, year=None):
        """Generar tarjeta desde BIN, parcial o manual"""
        
        if not input_data:
            bin_num = random.choice(self.bins)
            card_number = self.generate_card_number(bin_num)
        else:
            if len(input_data) == 6 and input_data.isdigit():
                card_number = self.generate_card_number(input_data)
            elif 'X' in input_data.upper():
                card_number = self.generate_from_partial(input_data)
            elif len(input_data.replace(" ", "")) == 16:
                card_number = input_data.replace(" ", "")
            else:
                print(f"{Fore.RED}✗ Formato inválido")
                return None
        
        card_type = "VISA" if card_number.startswith('4') else "MASTERCARD" if card_number.startswith('5') else "UNKNOWN"
        
        return {
            'number': card_number,
            'exp_month': month or str(random.randint(1, 12)).zfill(2),
            'exp_year': year or str(random.randint(2024, 2028)),
            'cvc': str(random.randint(100, 999)),
            'card_type': card_type,
            'stripe_valid': None,
            'live': False,
            'source': 'generated'
        }
    
    def add_manual_card(self):
        """Agregar tarjeta manualmente completa"""
        print(f"\n{Fore.CYAN}=== AGREGAR TARJETA MANUAL ===")
        
        try:
            number = input("Número de tarjeta (16 dígitos): ").replace(" ", "")
            if len(number) != 16 or not number.isdigit():
                print(f"{Fore.RED}✗ Número debe tener 16 dígitos")
                return None
            
            exp_month = input("Mes de expiración (MM): ")
            exp_year = input("Año de expiración (YYYY): ")
            cvc = input("CVV: ")
            
            card_type = "VISA" if number.startswith('4') else "MASTERCARD" if number.startswith('5') else "UNKNOWN"
            
            return {
                'number': number,
                'exp_month': exp_month,
                'exp_year': exp_year,
                'cvc': cvc,
                'card_type': card_type,
                'stripe_valid': None,
                'live': False,
                'source': 'manual'
            }
        except:
            print(f"{Fore.RED}✗ Error en los datos")
            return None
    
    def generate_card_number(self, bin_num):
        """Generar número de tarjeta desde BIN"""
        number = bin_num
        for _ in range(15 - len(bin_num)):
            number += str(random.randint(0, 9))
        return self.luhn_complete(number)
    
    def luhn_complete(self, number):
        """Completar número con dígito verificador Luhn"""
        def luhn_checksum(card_number):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_number)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10
        
        for i in range(10):
            test_number = number + str(i)
            if luhn_checksum(test_number) == 0:
                return test_number
        return number + '0'
    
    def safe_validate_cc(self, cc_data):
        if not self.sk:
            return False, False, "No SK configurado"
        
        # Verificar si el SK está muerto
        if self.sk_status == 'dead':
            return False, False, "SK INVALIDO - No se puede validar"
        
        if self.sk_type == 'live' and self.session_validations >= 15:
            return False, False, "Límite de seguridad"
        
        try:
            headers = {
                'Authorization': f'Bearer {self.sk}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            data = {
                'card[number]': cc_data['number'],
                'card[exp_month]': cc_data['exp_month'],
                'card[exp_year]': cc_data['exp_year'],
                'card[cvc]': cc_data['cvc']
            }
            
            if self.sk_type == 'live':
                time.sleep(1.5)
            
            response = requests.post(
                'https://api.stripe.com/v1/tokens',
                headers=headers,
                data=data,
                timeout=10
            )
            
            self.session_validations += 1
            is_valid = False
            is_live = False
            
            if response.status_code == 200:
                is_valid = True
                if self.sk_type == 'live':
                    is_live = True
                    return is_valid, is_live, "LIVE - Tarjeta real"
                else:
                    return is_valid, is_live, "VÁLIDA - Tarjeta de prueba"
            else:
                return False, False, "INVÁLIDA"
                
        except Exception as e:
            return False, False, f"Error: {str(e)}"
    
    def generate_multiple_cc(self):
        """Menú mejorado de generación"""
        print(f"\n{Fore.CYAN}=== GENERAR TARJETAS ===")
        print(f"{Fore.YELLOW}1. Con BIN (6 dígitos)")
        print(f"{Fore.YELLOW}2. Con número parcial (usar X para dígitos faltantes)")
        print(f"{Fore.YELLOW}3. Agregar tarjeta manual completa")
        
        try:
            option = input("Selecciona opción (1/2/3): ")
            
            if option == '1':
                max_limit = 100 if self.sk_type == 'test' else 20
                count = int(input(f"¿Cuántas tarjetas? (1-{max_limit}): "))
                
                if count < 1 or count > max_limit:
                    print(f"{Fore.RED}✗ Número inválido")
                    return
                
                print(f"\n{Fore.CYAN}BINs disponibles: {', '.join(self.bins[:8])}...")
                bin_input = input("BIN (6 dígitos - dejar vacío para aleatorio): ") or None
                
                month = input("Mes (MM - vacío para aleatorio): ") or None
                year = input("Año (YYYY - vacío para aleatorio): ") or None
                
                print(f"{Fore.YELLOW}Generando {count} tarjetas...")
                new_cards = []
                
                for i in range(count):
                    card = self.generate_cc(bin_input, month, year)
                    if card:
                        new_cards.append(card)
                        print(f"{Fore.WHITE}[{i+1}/{count}] {card['number']} | {card['card_type']}")
                
                self.generated_cards.extend(new_cards)
                print(f"{Fore.GREEN}✓ {count} tarjetas generadas desde BIN")
                
            elif option == '2':
                print(f"\n{Fore.CYAN}=== GENERAR CON NÚMERO PARCIAL ===")
                print(f"{Fore.YELLOW}Ejemplos:")
                print(f"{Fore.WHITE}• 411111XXXXXX1234  - 6 dígitos aleatorios")
                print(f"{Fore.WHITE}• 51XXXXXXXXXXXXXX  - 14 dígitos aleatorios")
                print(f"{Fore.WHITE}• 4532XX1234XXXXXX  - dígitos específicos + aleatorios")
                
                partial = input("\nIngresa número parcial (usar X): ").replace(" ", "")
                
                if not any(char.upper() == 'X' for char in partial):
                    print(f"{Fore.RED}✗ Debes usar X para dígitos faltantes")
                    return
                
                count = int(input("¿Cuántas variaciones generar? (1-50): "))
                if count < 1 or count > 50:
                    print(f"{Fore.RED}✗ Número inválido")
                    return
                
                month = input("Mes (MM - vacío para aleatorio): ") or None
                year = input("Año (YYYY - vacío para aleatorio): ") or None
                
                print(f"{Fore.YELLOW}Generando {count} variaciones...")
                new_cards = []
                
                for i in range(count):
                    card = self.generate_cc(partial, month, year)
                    if card:
                        new_cards.append(card)
                        print(f"{Fore.WHITE}[{i+1}/{count}] {card['number']} | {card['card_type']}")
                
                self.generated_cards.extend(new_cards)
                print(f"{Fore.GREEN}✓ {count} variaciones generadas")
                
            elif option == '3':
                card = self.add_manual_card()
                if card:
                    self.generated_cards.append(card)
                    print(f"{Fore.GREEN}✓ Tarjeta manual agregada: {card['number']}")
            
        except ValueError:
            print(f"{Fore.RED}✗ Ingresa un número válido")
        except Exception as e:
            print(f"{Fore.RED}✗ Error: {str(e)}")
    
    def validate_with_protection(self):
        if not self.sk:
            print(f"{Fore.RED}✗ Configura primero el SK")
            return
        
        if self.sk_status == 'dead':
            print(f"{Fore.RED}✗ SK INVALIDO - No se pueden hacer validaciones")
            return
        
        if not self.generated_cards:
            print(f"{Fore.RED}✗ No hay tarjetas generadas")
            return
        
        if self.sk_type == 'live':
            max_to_validate = min(15, len(self.generated_cards))
            remaining = 15 - self.session_validations
            if remaining <= 0:
                print(f"{Fore.RED}✗ Límite alcanzado")
                return
            max_to_validate = min(max_to_validate, remaining)
        else:
            max_to_validate = len(self.generated_cards)
        
        cards_to_validate = self.generated_cards[:max_to_validate]
        
        print(f"\n{Fore.CYAN}=== VALIDANDO {len(cards_to_validate)} TARJETAS ===")
        
        valid_count = 0
        live_count = 0
        
        for i, card in enumerate(cards_to_validate, 1):
            print(f"{Fore.WHITE}[{i}/{len(cards_to_validate)}] {card['number']}... ", end="")
            
            is_valid, is_live, message = self.safe_validate_cc(card)
            card['stripe_valid'] = is_valid
            card['live'] = is_live
            
            if is_live:
                print(f"{Fore.GREEN}LIVE ✓")
                live_count += 1
                valid_count += 1
            elif is_valid:
                print(f"{Fore.CYAN}VÁLIDA ✓")
                valid_count += 1
            else:
                print(f"{Fore.RED}INVÁLIDA ✗")
        
        print(f"\n{Fore.GREEN}=== RESULTADOS ===")
        print(f"{Fore.WHITE}Total: {len(cards_to_validate)}")
        print(f"{Fore.CYAN}Válidas: {valid_count}")
        print(f"{Fore.GREEN}LIVE: {live_count}")
        print(f"{Fore.RED}Inválidas: {len(cards_to_validate)-valid_count}")
    
    def show_menu(self):
        # Determinar color del estado del SK
        if self.sk_status == 'live':
            sk_color = Fore.GREEN
            sk_status_text = "LIVE ✅"
        elif self.sk_status == 'dead':
            sk_color = Fore.RED
            sk_status_text = "DEAD ❌"
        else:
            sk_color = Fore.YELLOW
            sk_status_text = "UNKNOWN ⚠️"
        
        sk_type_text = f"{Fore.GREEN}LIVE" if self.sk_type == 'live' else f"{Fore.CYAN}TEST"
        
        print(f"\n{Fore.MAGENTA}=== CHECKER CC - MODO {sk_type_text} ===")
        print(f"{Fore.CYAN}SK: {'✓' if self.sk else '✗'} | Estado: {sk_color}{sk_status_text}")
        print(f"{Fore.CYAN}Tarjetas: {len(self.generated_cards)} | Validadas: {self.session_validations}")
        
        if self.sk_type == 'live':
            remaining = max(0, 15 - self.session_validations)
            print(f"{Fore.RED}Límite restante: {remaining}/15")
        
        print(f"{Fore.YELLOW}1. Configurar Stripe SK")
        print(f"{Fore.YELLOW}2. Generar/Agregar tarjetas")
        print(f"{Fore.YELLOW}3. Validar tarjetas")
        print(f"{Fore.YELLOW}4. Mostrar tarjetas")
        print(f"{Fore.YELLOW}5. Limpiar todas las tarjetas")
        print(f"{Fore.YELLOW}0. Salir")
        
        return input(f"\n{Fore.GREEN}Selecciona opción: ")
    
    def clear_cards(self):
        """Limpiar todas las tarjetas"""
        confirm = input(f"{Fore.RED}¿Eliminar TODAS las tarjetas? (s/n): ").lower()
        if confirm == 's':
            self.generated_cards = []
            self.valid_cards = []
            print(f"{Fore.GREEN}✓ Todas las tarjetas eliminadas")
    
    def run(self):
        print(f"{Fore.CYAN}=== CHECKER CC - USO EDUCATIVO ===")
        
        while True:
            choice = self.show_menu()
            
            if choice == '1':
                self.set_stripe_key()
            elif choice == '2':
                self.generate_multiple_cc()
            elif choice == '3':
                self.validate_with_protection()
            elif choice == '4':
                if not self.generated_cards:
                    print(f"{Fore.RED}✗ No hay tarjetas")
                else:
                    print(f"\n{Fore.CYAN}=== TARJETAS ({len(self.generated_cards)}) ===")
                    for i, card in enumerate(self.generated_cards, 1):
                        color = Fore.GREEN if card.get('live') else Fore.CYAN if card.get('stripe_valid') else Fore.RED if card.get('stripe_valid') is False else Fore.YELLOW
                        status = "LIVE" if card.get('live') else "VÁLIDA" if card.get('stripe_valid') else "INVÁLIDA" if card.get('stripe_valid') is False else "NO VALIDADA"
                        source = f"({card.get('source', 'generated')})"
                        print(f"{i}. {color}{card['number']} | {status} {source}")
            elif choice == '5':
                self.clear_cards()
            elif choice == '0':
                print(f"{Fore.GREEN}¡Hasta luego!")
                break
            else:
                print(f"{Fore.RED}Opción inválida")
            
            input(f"\n{Fore.YELLOW}Enter para continuar...")

if __name__ == "__main__":
    checker = SecureCCChecker()
    checker.run()
