# -*- coding: utf-8 -*-
import datetime
import logging
from collections import defaultdict
from datetime import datetime
from . import base
import socket

import pytz

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, time


_logger = logging.getLogger(__name__)

try:
    from .base import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connect the biometric device with odoo"""
    _name = 'biometric.device.details'
    _description = 'Biometric Device Details'

    name = fields.Char(string='Name', required=True, help='Record Name')
    device_ip = fields.Char(string='Device IP', required=True,
                            help='The IP address of the Device')
    port_number = fields.Integer(string='Port Number 1', required=True,
                                 help="The Port Number of the Device")
    port_number2 = fields.Integer(string='Port Number 2', required=True,
                                  help="The Port Number of the Device")
    port_number3 = fields.Integer(string='Port Number 3', required=True,
                                  help="The Port Number of the Device")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda
                                     self: self.env.user.company_id.id,
                                 help='Current Company')
    date_to = fields.Date(string="Date Range", default=fields.Date.today)
    date_from = fields.Date(string="Date from", default=fields.Date.today)
    log_details = fields.Text(string='Logs de Conexión', readonly=True)
    ommit_ping = fields.Boolean(string='Omitir ping',default =False)
    last_attendance_download = fields.Datetime(
        string='Última descarga de asistencia',
        help='Marca la última marca de asistencia descargada para evitar duplicados.'
    )
    pin = fields.Char(string="PIN", size=4)

    @api.constrains('pin')
    def _check_pin_is_numeric(self):
        for record in self:
            if record.pin and not record.pin.isdigit():
                raise ValidationError("El PIN debe contener solo números.")
                
    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        try:
            conn = zk.connect()
            return conn
        except Exception:
            return False


    def test_vanshui_connection(self):
        ip = self.device_ip
        port = self.port_number
        timeout = 5
    
        # --- Paso 1: Autenticación con CommKey 0 ---
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))
    
            # Enviar CommKey 0
            auth_command = "~Pin=0\r\n"
            sock.send(auth_command.encode('ascii'))
            auth_response = sock.recv(1024).decode('ascii', errors='ignore')
            _logger.info(f"Respuesta de autenticación: [{auth_response.strip()}]")
    
            # --- Paso 2: Enviar comando ~Platform ---
            activate_command = "~ZK200\r\n"
            sock.send(activate_command.encode('ascii'))
            activate_response = sock.recv(1024).decode('ascii', errors='ignore')
            _logger.info(f"Respuesta de activación ZK200: [{activate_response.strip()}]")
    
            # --- Paso 3: Enviar comando ~Device ---
            device_command = "~Device\r\n"
            sock.send(device_command.encode('ascii'))
            device_response = sock.recv(1024).decode('ascii', errors='ignore')
            _logger.info(f"Respuesta de Device: [{device_response.strip()}]")
    
            sock.close()
    
            # Si alguna respuesta no está vacía, ¡éxito!
            if activate_response.strip() or device_response.strip():
                _logger.info("🎉 ¡ÉXITO! El reloj respondió a un comando.")
                return True
    
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return False
    
        _logger.error("❌ El reloj no respondió a ningún comando.")
        return False

    
       
        
    @api.model
    def cron_download_attendance(self):
        """cron_download method: Perform a cron job to download attendance data for all machines.

          This method iterates through all the machines in the 'zk.machine' model and
          triggers the download_attendance method for each machine."""
        _logger.info("++++++++++++Cron Executed++++++++++++++++++++++")
        machines = self.env['biometric.device.details'].search([])
        for machine in machines:
            machine.action_download_attendance()



    def action_test_connection(self):
        """Checking the connection status and storing logs in log_details field"""
        success_ports = []
        error_ports = []
        log_message = ""
        password = int(self.pin) if self.pin else 0
        def log_append(message):
            nonlocal log_message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message += f'[{timestamp}] {message}\n'
    
        # Recuperar los logs anteriores
        existing_logs = self.log_details or ""
    
        if self.port_number:
            zk_1 = ZK(self.device_ip, port=self.port_number, timeout=30,
                      password=password,force_udp=False, ommit_ping=self.ommit_ping)
            try:
                conn = zk_1.connect()
                if conn:
                    success_ports.append(self.port_number)
                    log_append(f'✅ Puerto {self.port_number}: Conexión exitosa.')
                else:
                    error_ports.append(self.port_number)
                    log_append(f'❌ Puerto {self.port_number}: No se pudo conectar.')
            except Exception as e:
                error_ports.append(self.port_number)
                log_append(f'❌ Puerto {self.port_number}: Error - {str(e)}')
    
        if self.port_number2:
            zk_2 = ZK(self.device_ip, port=self.port_number2, timeout=30,
                      password=False, ommit_ping=False)
            try:
                conn = zk_2.connect()
                if conn:
                    success_ports.append(self.port_number2)
                    log_append(f'✅ Puerto {self.port_number2}: Conexión exitosa.')
                else:
                    error_ports.append(self.port_number2)
                    log_append(f'❌ Puerto {self.port_number2}: No se pudo conectar.')
            except Exception as e:
                error_ports.append(self.port_number2)
                log_append(f'❌ Puerto {self.port_number2}: Error - {str(e)}')
    
        if self.port_number3:
            zk_3 = ZK(self.device_ip, port=self.port_number3, timeout=30,
                      password=False, ommit_ping=False)
            try:
                conn = zk_3.connect()
                if conn:
                    success_ports.append(self.port_number3)
                    log_append(f'✅ Puerto {self.port_number3}: Conexión exitosa.')
                else:
                    error_ports.append(self.port_number3)
                    log_append(f'❌ Puerto {self.port_number3}: No se pudo conectar.')
            except Exception as e:
                error_ports.append(self.port_number3)
                log_append(f'❌ Puerto {self.port_number3}: Error - {str(e)}')
    
        # Concatenar los nuevos logs con los existentes
        full_log = existing_logs + "\n" + log_message.strip()
    
        # Guardar los logs acumulados
        for record in self:
            record.log_details = full_log
    
        message = ""
        if success_ports:
            message += f'Successfully connected to ports: {success_ports}. '
        if error_ports:
            message += f'Failed to connect to ports: {error_ports}.'
    
        if success_ports:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': False
                }
            }
        else:
            return

    def action_download_attendance(self):
        """Function to download attendance records from the device (Single Port Version)"""
        zk_attendance = self.env['zk.machine.attendance']
        hr_attendance = self.env['hr.attendance']
        log_message = ""
        password = int(self.pin) if self.pin else 0
    
        def log_append(message):
            nonlocal log_message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message += f"[{timestamp}] {message}\n"
    
        existing_logs = self.log_details or ""
    
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number  # Solo usamos un puerto
    
            log_append(f"🔌 Conectando a {machine_ip}:{zk_port}")
    
            try:
                # Conectar con el dispositivo
                zk = ZK(machine_ip, port=zk_port, timeout=10,
                        password=password, force_udp=False, ommit_ping=info.ommit_ping)
                conn = self.device_connect(zk)
                if not conn:
                    log_append(f"❌ No se pudo conectar al dispositivo en {machine_ip}:{zk_port}")
                    continue
    
                log_append(f"✅ Conexión exitosa a {machine_ip}:{zk_port}")
                conn.disable_device()
                attendance_data = conn.get_attendance()
                conn.disconnect()
                if not attendance_data:
                    log_append(f"⚠️ No se encontraron registros de asistencia en {machine_ip}")
                    continue
    
                log_append(f"📊 Descargados {len(attendance_data)} registros de asistencia")
    
                # Procesar registros
                last_download = info.last_attendance_download or datetime.min
                attendance_list = []
                for each in attendance_data:
                    _logger.info(each)
                    if each.status == 16:
                        _logger.info(f"⏭️ Ignorando registro con status=16: {each}")
                        continue
                    atten_time = each.timestamp
                    local_tz = pytz.timezone(self.env.user.partner_id.tz or 'GMT')
                    local_dt = local_tz.localize(atten_time, is_dst=None)
                    utc_dt = local_dt.astimezone(pytz.utc)
                    atten_time_datetime = utc_dt.replace(tzinfo=None)
                    _logger.info(f"🔍 PUNCH VALUE: {each.punch} | TYPE: {type(each.punch)}")
                    if atten_time_datetime <= last_download:
                        _logger.info(f"⏭️ Registro ya procesado anteriormente: {atten_time_datetime} (última descarga: {last_download})")
                        continue
                    attendance_list.append({
                        'user_id': each.user_id,
                        'timestamp': atten_time_datetime,
                        'punch': each.punch  # 0 = entrada, 1 = salida
                    })
    
                # Agrupar por usuario
                # Eliminar marcas duplicadas (mismo user_id, timestamp, punch)
                seen = set()
                unique_attendance_list = []
                for rec in attendance_list:
                    key = (rec['user_id'], rec['timestamp'], rec['punch'])
                    if key not in seen:
                        seen.add(key)
                        unique_attendance_list.append(rec)
                    else:
                        _logger.info(f"⏭️ Marca duplicada ignorada: {key}")
                attendance_list = unique_attendance_list
                user_attendance = defaultdict(list)
                for rec in attendance_list:
                    user_attendance[rec['user_id']].append(rec)
    
                # Procesar cada usuario
                for user_id, records in user_attendance.items():
                    employee = self.env['hr.employee'].search([('device_id_num', '=', user_id)], limit=1)
                    if not employee:
                        log_append(f"⚠️ Empleado con device_id {user_id} no encontrado")
                        continue
    
                    # ✅ Cerrar SOLO registros abiertos de días ANTERIORES al primer nuevo registro
                    if records:
                        first_new_time = min(rec['timestamp'] for rec in records)
                        first_new_date = first_new_time.date()
    
                        # Buscar registros abiertos con check_in en fecha anterior al primer nuevo registro
                        open_hr_records = hr_attendance.search([
                            ('employee_id', '=', employee.id),
                            ('check_out', '=', False),
                            ('check_in', '<', datetime.combine(first_new_date, datetime.min.time()))
                        ])
                        _logger.info(open_hr_records)
                        if open_hr_records:
                            for open_rec in open_hr_records:
                                # Cerrar a las 23:59:59 del día de la entrada
                                _logger.info(open_rec)
                                close_time = datetime.combine(open_rec.check_in.date(), datetime.max.time())
                                close_time -= timedelta(hours=1)
                                
                                # Asegurar que no sobrepase el primer nuevo registro (por seguridad)
                                if close_time >= first_new_time:
                                    close_time = first_new_time - timedelta(hours=1)
                                    if close_time < open_rec.check_in:
                                        close_time = open_rec.check_in
                                
                                _logger.info("Close time") 
                                _logger.info(close_time)
                                
                                # VERIFICAR Y ELIMINAR REGISTROS DUPLICADOS DE HORAS EXTRAS ANTES DE CERRAR
                                overtime_records = self.env['hr.attendance.overtime'].search([
                                    ('employee_id', '=', employee.id),
                                    ('date', '=', open_rec.check_in.date())
                                ])
                                
                                if overtime_records:
                                    # Mantener solo el primer registro y eliminar los duplicados
                                    overtime_records[1:].unlink()
                                    _logger.info(f"🗑️ Eliminados {len(overtime_records) - 1} registros duplicados de horas extras para {employee.name} del día {open_rec.check_in.date()}")
                                
                                # Cerrar el registro de asistencia
                                open_rec.write({'check_out': open_rec.check_in})
                        
                                zk_open = zk_attendance.search([
                                    ('employee_id', '=', employee.id),
                                    ('check_in', '=', open_rec.check_in),
                                    ('check_out', '=', False)
                                ], limit=1)
                                
                                if zk_open:
                                    zk_open.write({
                                        'check_out': close_time,
                                        'o_check': 'o',
                                    })
                                
                                log_append(f"🔧 EMPLEADO {employee.name}: Registro abierto del {open_rec.check_in.date()} "
                                           f"cerrado automáticamente a las {close_time}.")
    
                    # Ahora sí, agrupar registros por día
                    records_by_day = defaultdict(list)
                    for rec in records:
                        day = rec['timestamp'].date()
                        records_by_day[day].append(rec)
    
                    # Procesar cada día
                    for day, daily_records in records_by_day.items():
                        # Ordenar cronológicamente dentro del día
                        daily_records.sort(key=lambda x: x['timestamp'])
                        for record in daily_records:
                            punch = record['punch']
                            atten_time = record['timestamp']
                            employee_id = employee.id
    
                            if punch == 0:  # Entrada
                                # Buscar registro ABIERTO del MISMO DÍA
                                open_hr = hr_attendance.search([
                                    ('employee_id', '=', employee_id),
                                    ('check_in', '>=', datetime.combine(day, datetime.min.time())),
                                    ('check_in', '<=', datetime.combine(day, datetime.max.time())),
                                    ('check_out', '=', False)
                                ], order='check_in desc', limit=1)
    
                                if open_hr:
                                    # Cerrar registro anterior (doble entrada)
                                    open_hr.write({'check_out': atten_time})
                                    zk_open = zk_attendance.search([
                                        ('employee_id', '=', employee_id),
                                        ('check_in', '=', open_hr.check_in),
                                        ('check_out', '=', False)
                                    ], limit=1)
                                    if zk_open:
                                        zk_open.write({
                                            'check_out': atten_time,
                                            'o_check': 'o',
                                        })
                                    log_append(f"🔄 EMPLEADO {employee.name} ({day}): Registro anterior cerrado por doble entrada a las {atten_time}.")
    
                                # Crear NUEVO registro de entrada en ambos modelos
                                existing_entry = hr_attendance.search([
                                    ('employee_id', '=', employee_id),
                                    ('check_in', '=', atten_time)
                                ], limit=1)

                                if not existing_entry:
                                    hr_rec = hr_attendance.create({
                                        'employee_id': employee_id,
                                        'check_in': atten_time,
                                    })
                                    zk_attendance.create({
                                        'employee_id': employee_id,
                                        'check_in': atten_time,
                                        'device_id_num': user_id,
                                        'i_check': 'i',
                                    })
                                    log_append(f"📥 EMPLEADO {employee.name} ({day}): Nueva entrada registrada a las {atten_time}.")
                                else:
                                    log_append(f"⏭️ EMPLEADO {employee.name} ({day}): Entrada ya existente a las {atten_time}. Ignorada.")
    
                            elif punch == 1:  # Salida
                                open_hr = hr_attendance.search([
                                    ('employee_id', '=', employee_id),
                                    ('check_in', '>=', datetime.combine(day, datetime.min.time())),
                                    ('check_in', '<=', datetime.combine(day, datetime.max.time())),
                                    ('check_out', '=', False)
                                ], order='check_in desc', limit=1)
    
                                if open_hr:
                                    open_hr.write({'check_out': atten_time})
                                    zk_open = zk_attendance.search([
                                        ('employee_id', '=', employee_id),
                                        ('check_in', '=', open_hr.check_in),
                                        ('check_out', '=', False)
                                    ], limit=1)
                                    if zk_open:
                                        zk_open.write({
                                            'check_out': atten_time,
                                            'o_check': 'o',
                                        })
                                    log_append(f"📤 EMPLEADO {employee.name} ({day}): Salida registrada, cerrando entrada de {open_hr.check_in}.")
                                else:
                                    # No hay entrada → crear entrada 10 min antes
                                    fake_check_in = atten_time - timedelta(minutes=10)
                                    # Verificar si ya existe un registro con esta salida
                                    existing_exit = hr_attendance.search([
                                        ('employee_id', '=', employee_id),
                                        ('check_out', '=', atten_time)
                                    ], limit=1)
    
                                    if not existing_exit:
                                        hr_rec = hr_attendance.create({
                                            'employee_id': employee_id,
                                            'check_in': fake_check_in,
                                            'check_out': atten_time,
                                        })
                                        zk_attendance.create({
                                            'employee_id': employee_id,
                                            'check_in': fake_check_in,
                                            'check_out': atten_time,
                                            'device_id_num': user_id,
                                            'i_check': 'i',
                                            'o_check': 'o',
                                        })
                                        log_append(f"⚠️ EMPLEADO {employee.name} ({day}): Salida sin entrada. "
                                                   f"Creada entrada simulada a las {fake_check_in} y salida a las {atten_time}.")
                                    else:
                                        log_append(f"⏭️ EMPLEADO {employee.name} ({day}): Salida ya existente a las {atten_time}. Ignorada.")
    
                            else:
                                log_append(f"❓ EMPLEADO {employee.name} ({day}): Punch desconocido ({punch}). Ignorado.")
    
                if attendance_list:
                    latest_timestamp = max(rec['timestamp'] for rec in attendance_list)
                    info.write({'last_attendance_download': latest_timestamp})
                    log_append(f"✅ Última marca procesada: {latest_timestamp}")
                log_append(f"✅ Desconectado de {machine_ip}")
    
            except Exception as e:
                log_append(f"❌ Error al procesar el dispositivo {machine_ip}: {str(e)}")
    
        # Guardar logs acumulados
        full_log = existing_logs + "\n" + log_message.strip()
        self.write({'log_details': full_log})
    
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Descarga de asistencia completada. Ver logs para detalles.',
                'type': 'success',
                'sticky': False
            }
        }
    def clean_logs(self):
        for record in self:
            record.log_details = ''


    def action_restart_device(self):
        """For restarting the device"""
        try:

            zk_1 = ZK(self.device_ip, port=self.port_number, timeout=30,
                      password=0,
                      force_udp=False, ommit_ping=False)
            zk_2 = ZK(self.device_ip, port=self.port_number2, timeout=30,
                      password=0,
                      force_udp=False, ommit_ping=False)
            zk_5 = ZK(self.device_ip, port=self.port_number3, timeout=30,
                      password=0,
                      force_udp=False, ommit_ping=False)
            self.device_connect(zk_1).restart()
            self.device_connect(zk_2).restart()
            self.device_connect(zk_5).restart()
        except Exception as error:
            raise ValidationError(f'{error}')
