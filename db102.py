import os
import ctypes
import snap7
from snap7.util import *
from snap7.type import Areas
import time
from datetime import datetime


# ----------- Configuration ----------- #
PLC_IP = "192.0.0.2"
RACK = 0
SLOT = 0
DLL_PATH = os.path.abspath("snap7.dll")


# ----------- DLL Load ----------- #
if not os.path.exists(DLL_PATH):
    raise FileNotFoundError("❌ snap7.dll not found. Please add it next to your script.")

ctypes.CDLL(DLL_PATH)


# ----------- PLC Analyzer Class ----------- #
class PLCAnalyzer:
    def __init__(self, ip, rack=0, slot=0):
        self.client = snap7.client.Client()
        self.client.connect(ip, rack, slot)
        if not self.client.get_connected():
            raise ConnectionError("❌ PLC connection failed")
        print(f"✅ Connected to PLC at {ip}")
        try:
                blocks = self.client.list_blocks()
                print("✅ Blocks found:")
                print(f"  OB:  {blocks.OBCount}")
                print(f"  FB:  {blocks.FBCount}")
                print(f"  FC:  {blocks.FCCount}")
                print(f"  SFB: {blocks.SFBCount}")
                print(f"  SFC: {blocks.SFCCount}")
                print(f"  DB:  {blocks.DBCount}")
                print(f"  SDB: {blocks.SDBCount}")
        except Exception as e:
                print(f"❌ Error listing blocks: {e}")


    def read_raw_db(self, db_number):
        try:
            return self.client.upload(db_number)
        except Exception as e:
            print(f"❌ Error reading DB{db_number}: {e}")
            return None
    
    def export_raw_to_file(self, db_number, raw_bytes, export_dir="dumps"):
        os.makedirs(export_dir, exist_ok=True)
        hex_str = raw_bytes.hex()
        with open(f"{export_dir}/DB{db_number}_raw.txt", "w") as f:
            f.write(hex_str)


    def scan_and_decode_db(self, db_number):
        print(f"\n{'='*60}\nScanning DB{db_number}\n{'='*60}")
        raw_bytes = self.read_raw_db(db_number)
        if raw_bytes is None:
            return

        print(f"Raw bytes read: {raw_bytes}")
        print(f"DB{db_number} Size: {len(raw_bytes)} bytes")
        print(f"Hex dump       : {raw_bytes.hex()}")
        self.export_raw_to_file(db_number, raw_bytes)


    def extract_specific_values_from_db102(self):
        """Extract specific REAL values from DB102 at predefined offsets"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}\nExtracting Specific Values from DB102 - {timestamp}\n{'='*60}")
        
        # Define the offsets and their descriptions
        offsets_info = {
            # 98:  "VALUE._04_Temp_hydr_R - Température du système hydraulique",
            # 250: "VALUE._11_H_height_actual_R - Hauteur de levage (codeur absolu)",
            # 378: "VALUE._12_H_height_actual_R - Hauteur de levage (codeur absolu)",
            # 516: "VALUE._21_RAD_actual_R - Angle d'orientation superstructure",
            # 946: "VALUE._63_Bruttoload_relativ_R - Charge brute relative",
            # 910: "VALUE._63_Nettoload_R - Charge nette en tonnes",
            # 868: "VALUE._61_B12_Angle_X_R - Calage: angle de l'axe X",
            # 872: "VALUE._61_B12_Angle_Y_R - Calage: angle de l'axe Y",
            # 892: "VALUE._61_Wind_actual_R - Vitesse du vent valeur réelle",
            # 122: "VALUE._07_Fuel_level_cent_R - Niveau de carburant diesel (%)"
0: "VALUE._01_Power_kW_R - Puissance en kW (kW)",
4: "VALUE._02_Measured_power_kW_R - Puissance mesurée en kW (kW)",
54: "VALUE._03_Braking_rectifier_network_voltage_V_R - Tension du réseau du redresseur de freinage (V)",
58: "VALUE._04_Network_frequency_Hz_R - Fréquence du réseau (Hz)",
82: "VALUE._05_Reduced_setpoint_hydraulic_pump_percent_R - Consigne réduite pour pompe hydraulique (%)",
94: "VALUE._06_Hydraulic_pump_setpoint_percent_R - Consigne pompe hydraulique (%)",
98: "VALUE._07_Hydraulic_system_temperature_degC_R - Température système hydraulique (°C)",
102: "VALUE._08_Actual_pump_pressure_bar_R - Pression réelle de la pompe (bar)",
122: "VALUE._09_Diesel_fuel_tank_fill_level_percent_R - Niveau de carburant diesel (%)",
182: "VALUE._10_Reduce_speed_setpoint_power_reduction_percent_R - Réduction de vitesse par réduction de puissance (%)",
186: "VALUE._11_Calculate_speed_setpoint_hoist_load_percent_R - Calculer la consigne de vitesse mécanisme de levage selon charge (%)",
190: "VALUE._12_Apply_end_of_travel_value_command_steps_percent_R - Appliquer la valeur de fin de course et la commande par paliers (%)",
202: "VALUE._13_Hoist_target_point_reduced_setpoint_percent_R - Levage vers point cible avec consigne réduite (%)",
206: "VALUE._14_Setpoint_transmission_drive_percent_R - Transmission de la consigne au variateur (%)",
218: "VALUE._15_Actual_speed_rpm_R - Vitesse réelle (rpm)",
222: "VALUE._16_Actual_current_A_R - Courant réel (A)",
226: "VALUE._17_Actual_power_kW_R - Puissance réelle (kW)",
230: "VALUE._18_Actual_motor_voltage_V_R - Tension moteur réelle (V)",
234: "VALUE._19_Actual_mains_frequency_Hz_R - Fréquence réseau réelle (Hz)",
242: "VALUE._20_Actual_motor_temperature_degC_R - Température moteur réelle (°C)",
250: "VALUE._21_Actual_lifting_height_m_absolute_encoder_R - Hauteur de levage réelle (encodeur absolu) (m)",
262: "VALUE._22_Service_pressure_hoist_brake_bar_R - Pression de service frein mécanisme levage (bar)",
270: "VALUE._23_Hoist_mechanism_permissible_speed_m_per_min_R - Vitesse admissible mécanisme levage (m/min)",
280: "VALUE._24_Hoist_mechanism_gearbox_oil_temperature_degC_R - Température huile boîte de vitesses mécanisme levage (°C)",
312: "VALUE._25_Hoist_mechanism_permissible_speed_rpm_R - Vitesse admissible mécanisme levage (rpm)",
316: "VALUE._26_Hoist_setpoint_manipulator_percent_R - Consigne levage via manipulateur (%)",
326: "VALUE._27_Order_read_adjust_setpoint_percent_R - Ordre : lecture et ajustement de la consigne (%)",
330: "VALUE._28_Setpoint_transmission_drive_percent_R - Transmission de la consigne au variateur (%)",
378: "VALUE._29_Actual_lifting_height_m_absolute_encoder_R - Hauteur de levage réelle (encodeur absolu) (m)",
390: "VALUE._30_Service_pressure_closing_mechanism_brake_bar_R - Pression de service frein mécanisme fermeture (bar)",
464: "VALUE._31_Order_read_adjust_setpoint_percent_R - Ordre : lecture et ajustement de la consigne (%)",
472: "VALUE._32_Calculate_slew_speed_outreach_percent_R - Calculer la consigne de vitesse rotation selon portée (%)",
476: "VALUE._33_Setpoint_transmission_drive_percent_R - Transmission de la consigne au variateur (%)",
496: "VALUE._34_Actual_speed_rpm_R - Vitesse réelle (rpm)",
500: "VALUE._35_Actual_current_A_R - Courant réel (A)",
508: "VALUE._36_Actual_motor_voltage_V_R - Tension moteur réelle (V)",
512: "VALUE._37_Actual_motor_temperature_degC_R - Température moteur réelle (°C)",
516: "VALUE._38_Actual_slewing_angle_superstructure_chassis_deg_R - Angle de rotation réel châssis superstructure (degrés)",
520: "VALUE._39_Actual_acceleration_time_seconds_R - Temps d'accélération réel (secondes)",
528: "VALUE._40_Motor_speed_setpoint_percent_R - Consigne vitesse moteur (%)",
532: "VALUE._41_Maximum_crane_speed_rpm_R - Vitesse maximale grue (rpm)",
538: "VALUE._42_Reduced_maximum_peripheral_speed_m_per_min_R - Vitesse périphérique maximale réduite (m/min)",
542: "VALUE._43_Reduced_maximum_slew_speed_rpm_R - Vitesse de rotation maximale réduite (rpm)",
578: "VALUE._44_Slew_setpoint_manipulator_percent_R - Consigne rotation via manipulateur (%)",
592: "VALUE._45_Boom_raising_calculate_permissible_outreach_m_R - Calcul portée admissible levage flèche (m)",
596: "VALUE._46_Boom_lowering_calculate_permissible_outreach_m_R - Calcul portée admissible descente flèche (m)",
640: "VALUE._47_Actual_luffing_cylinder_speed_mm_per_s_or_m_per_min_R - Vitesse réelle vérin de flèche (mm/s ou m/min)",
652: "VALUE._48_Outreach_m_absolute_encoder_R - Portée (encodeur absolu) (m)",
664: "VALUE._49_Luffing_setpoint_manipulator_percent_R - Consigne flèche via manipulateur (%)",
674: "VALUE._50_Pressure_luffing_piston_side_bar_R - Pression côté piston vérin de flèche (bar)",
678: "VALUE._51_Travel_setpoint_percent_R - Consigne déplacement (%)",
682: "VALUE._52_Frequency_setpoint_Hz_R - Consigne fréquence (Hz)",
686: "VALUE._53_Actual_speed_rpm_R - Vitesse réelle (rpm)",
694: "VALUE._54_Actual_current_A_R - Courant réel (A)",
698: "VALUE._55_Intermediate_circuit_voltage_V_R - Tension circuit intermédiaire (V)",
702: "VALUE._56_Output_voltage_V_R - Tension de sortie (V)",
710: "VALUE._57_Order_read_adjust_setpoint_percent_R - Ordre : lecture et ajustement de la consigne (%)",
714: "VALUE._58_Order_read_adjust_setpoint_percent_R - Ordre : lecture et ajustement de la consigne (%)",
860: "VALUE._59_Calibration_angle_X_axis_deg_R - Calibration : angle axe X (degrés)",
864: "VALUE._60_Calibration_angle_Y_axis_deg_R - Calibration : angle axe Y (degrés)",
868: "VALUE._61_Calibration_angle_X_axis_deg_R - Calibration : angle axe X (degrés)",
872: "VALUE._62_Calibration_angle_Y_axis_deg_R - Calibration : angle axe Y (degrés)",
892: "VALUE._63_Actual_wind_speed_m_per_s_R - Vitesse du vent réelle (m/s)",
902: "VALUE._64_Gross_load_tonnes_R - Charge totale (tonnes)",
910: "VALUE._65_Net_load_tonnes_R - Charge nette (tonnes)",
926: "VALUE._66_Permitted_gross_load_tonnes_R - Charge totale autorisée (tonnes)",
938: "VALUE._67_Outreach_meters_R - Portée (mètres)",
946: "VALUE._68_Relative_gross_load_percent_R - Charge totale relative (%)",
958: "VALUE._69_Hoist_load_spectrum_counter_unitless_R - Compteur spectre de charge levage (sans unité)",
1020: "VALUE._70_CEC_indicator_test_mode_actual_load_tonnes_R - Indicateur CEC, mode test : charge réelle (tonnes)",
1268: "VALUE._71_Permitted_outreach_boom_raise_no_limit_calc1_m_R - Portée admissible levage flèche sans limitation, calcul 1 (m)",
1292: "VALUE._72_Permitted_outreach_boom_raise_no_limit_calc2_m_R - Portée admissible levage flèche sans limitation, calcul 2 (m)",
1314: "VALUE._73_Hex_Value_R - Valeur hexadécimale",
1316: "VALUE._74_Pressure_1_front_right_side_piston_bar_R - Pression 1 côté avant droit (piston) (bar)",
1320: "VALUE._75_Pressure_1_front_right_side_rod_bar_R - Pression 1 côté avant droit (tige) (bar)",
1324: "VALUE._76_Pressure_1_rear_right_side_piston_bar_R - Pression 1 côté arrière droit (piston) (bar)",
1328: "VALUE._77_Pressure_1_rear_right_side_rod_bar_R - Pression 1 côté arrière droit (tige) (bar)",
1332: "VALUE._78_Pressure_1_rear_left_side_piston_bar_R - Pression 1 côté arrière gauche (piston) (bar)",
1336: "VALUE._79_Pressure_1_rear_left_side_rod_bar_R - Pression 1 côté arrière gauche (tige) (bar)",
1344: "VALUE._80_Pressure_2_front_left_side_rod_bar_R - Pression 2 côté avant gauche (tige) (bar)",
1348: "VALUE._81_Pressure_2_front_right_side_piston_bar_R - Pression 2 côté avant droit (piston) (bar)",
1352: "VALUE._82_Pressure_2_front_right_side_rod_bar_R - Pression 2 côté avant droit (tige) (bar)",
1356: "VALUE._83_Pressure_2_rear_right_side_piston_bar_R - Pression 2 côté arrière droit (piston) (bar)",
1360: "VALUE._84_Pressure_2_rear_right_side_rod_bar_R - Pression 2 côté arrière droit (tige) (bar)",
1364: "VALUE._85_Pressure_2_rear_left_side_piston_bar_R - Pression 2 côté arrière gauche (piston) (bar)",
1368: "VALUE._86_Pressure_2_rear_left_side_rod_bar_R - Pression 2 côté arrière gauche (tige) (bar)"
        }
        
        # Read DB102
        raw_bytes = self.read_raw_db(102)
        if raw_bytes is None:
            print("❌ Failed to read DB102")
            return
            
        print(f"DB102 Size: {len(raw_bytes)} bytes")
        
        # Extract and display each value
        extracted_values = {}
        for offset, description in offsets_info.items():
            try:
                # Check if we have enough bytes
                if offset + 4 <= len(raw_bytes):
                    # Extract REAL value at the specified offset
                    real_value = get_real(raw_bytes, offset)
                    extracted_values[offset] = real_value
                    print(f"Offset {offset:3d}: {real_value:12.3f} - {description}")
                else:
                    print(f"Offset {offset:3d}: ❌ Insufficient data (DB too small)")
            except Exception as e:
                print(f"Offset {offset:3d}: ❌ Error extracting value: {e}")
        
        # Export to file
        self.export_extracted_values_to_file(extracted_values, offsets_info, timestamp)
        return extracted_values


    def export_extracted_values_to_file(self, extracted_values, offsets_info, timestamp, export_dir="db-102-dumps"):
        """Export extracted values to a readable file"""
        os.makedirs(export_dir, exist_ok=True)
        
        with open(f"{export_dir}/DB102_extracted_values.txt", "a", encoding="utf-8") as f:
            f.write(f"\n\nExtracted Values from DB102 - {timestamp}\n")
            f.write("=" * 50 + "\n")
            
            for offset, description in offsets_info.items():
                if offset in extracted_values:
                    f.write(f"Offset {offset:3d}: {extracted_values[offset]:12.3f} - {description}\n")
                else:
                    f.write(f"Offset {offset:3d}: ❌ Not extracted - {description}\n")


# ----------- Entry ----------- #
def main():
    analyzer = PLCAnalyzer(PLC_IP, RACK, SLOT)
    
    # Continuous extraction every second
    try:
        while True:
            analyzer.extract_specific_values_from_db102()
            time.sleep(1)  # Wait 1 second before next extraction
    except KeyboardInterrupt:
        print("\n⏹️  Stopping data extraction...")
        print("✅ Program terminated by user")


if __name__ == "__main__":
    main()