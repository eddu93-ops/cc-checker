# CC Checker - Herramienta Educativa

🔍 **Checker de tarjetas para fines educativos y de laboratorio**

## ⚠️ ADVERTENCIA
Esta herramienta es SOLO para uso educativo en entornos controlados. No usar para actividades ilegales.

## Características
- ✅ Validación con Stripe API
- ✅ Generación de tarjetas (1-1000)
- ✅ BIN Lookup en tiempo real
- ✅ Sistema de colores para resultados
- ✅ Múltiples formatos de exportación

## Instalación en Termux
```bash
pkg update && pkg upgrade
pkg install python git
pip install requests colorama
git clone https://github.com/tu-usuario/cc-checker.git
cd cc-checker
python checker_cc_pro.py