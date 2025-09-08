# -*- coding: utf-8 -*-
import datetime
import logging
from collections import defaultdict
from datetime import datetime

import pytz

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, time


_logger = logging.getLogger(__name__)

try:
    from zk import ZK, const
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

    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        try:
            conn = zk.connect()
            return conn
        except Exception:
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
    
        def log_append(message):
            nonlocal log_message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message += f'[{timestamp}] {message}\n'
    
        # Recuperar los logs anteriores
        existing_logs = self.log_details or ""
    
        if self.port_number:
            zk_1 = ZK(self.device_ip, port=self.port_number, timeout=30,
                      password=False, ommit_ping=self.ommit_ping)
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
                zk = ZK(machine_ip, port=zk_port, timeout=30,
                        password=0, force_udp=False, ommit_ping=info.ommit_ping)
                conn = self.device_connect(zk)
                if not conn:
                    log_append(f"❌ No se pudo conectar al dispositivo en {machine_ip}:{zk_port}")
                    continue
    
                log_append(f"✅ Conexión exitosa a {machine_ip}:{zk_port}")
                conn.disable_device()
                attendance_data = conn.get_attendance()
    
                if not attendance_data:
                    log_append(f"⚠️ No se encontraron registros de asistencia en {machine_ip}")
                    conn.disconnect()
                    continue
    
                log_append(f"📊 Descargados {len(attendance_data)} registros de asistencia")
    
                # Procesar registros
                attendance_dict = defaultdict(list)
                for each in attendance_data:
                    _logger.info(each)
                    atten_time = each.timestamp
                    local_tz = pytz.timezone(self.env.user.partner_id.tz or 'GMT')
                    local_dt = local_tz.localize(atten_time, is_dst=None)
                    utc_dt = local_dt.astimezone(pytz.utc)
                    attendance_time = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                    atten_time_datetime = datetime.strptime(attendance_time, "%Y-%m-%d %H:%M:%S")
                    atten_date = atten_time_datetime.date()
    
                    if info.date_to <= atten_date <= info.date_from:
                        attendance_dict[each.user_id].append(atten_time_datetime)
    
                # Procesar por usuario
                for user_id, atten_times in attendance_dict.items():
                    dates = {}
                    for atten_time in atten_times:
                        atten_date = atten_time.date()
                        if atten_date not in dates:
                            dates[atten_date] = []
                        dates[atten_date].append(atten_time)
    
                    for atten_date, times in dates.items():
                        times.sort()
                        if len(times) > 2:
                            times = [times[0], times[-1]]
                        elif len(times) == 1 and atten_date != datetime.now().date():
                            employee = self.env['hr.employee'].search([('device_id_num', '=', user_id)])
                            if employee and employee.shift_id:
                                shift_out = employee.shift_id.shift_out
                                shift_out_time = time(int(shift_out - 5), int(((shift_out + 5) % 1) * 60))
                                checkout_datetime = datetime.combine(atten_date, shift_out_time)
                                times.append(checkout_datetime)
                                times.sort()
    
                        dates[atten_date] = times
    
                    updated_atten_times = [time for times in dates.values() for time in times]
                    updated_atten_times.sort()
    
                    employee = self.env['hr.employee'].search([('device_id_num', '=', user_id)])
                    if len(employee) == 1:
                        for atten_time in updated_atten_times:
                            existing_attendance = zk_attendance.search(
                                [('device_id_num', '=', user_id), ('check_out', '=', False)], limit=1)
                            existing_hr_attendance = hr_attendance.search(
                                [('employee_id', '=', employee.id), ('check_out', '=', False)], limit=1)
    
                            if existing_attendance:
                                exist = existing_attendance
                                if exist.check_in != atten_time:
                                    if exist.check_in.date() == atten_time.date():
                                        if exist.check_in > atten_time:
                                            exist.write({
                                                'check_in': atten_time,
                                                'check_out': exist.check_in,
                                                'o_check': 'o',
                                            })
                                        else:
                                            if exist.check_out:
                                                if exist.check_out < atten_time:
                                                    exist.write({
                                                        'check_out': atten_time,
                                                        'o_check': 'o',
                                                    })
                                                    if existing_hr_attendance:
                                                        existing_hr_attendance.write({
                                                            'check_out': atten_time
                                                        })
                                            else:
                                                exist.write({
                                                    'check_out': atten_time,
                                                    'o_check': 'o',
                                                })
                                                if existing_hr_attendance:
                                                    existing_hr_attendance.write({
                                                        'check_out': atten_time
                                                    })
                                    else:
                                        check_in_atten = zk_attendance.search(
                                            [('check_in', '=', atten_time), ('device_id_num', '=', user_id)])
                                        check_out_atten = zk_attendance.search(
                                            [('check_out', '=', atten_time), ('device_id_num', '=', user_id)])
                                        if not check_in_atten and not check_out_atten:
                                            zk_attendance.create({
                                                'employee_id': employee.id,
                                                'check_in': atten_time,
                                                'check_out': False,
                                                'i_check': 'i',
                                                'device_id_num': user_id
                                            })
                                            hr_attendance.create({
                                                'employee_id': employee.id,
                                                'check_in': atten_time
                                            })
                            else:
                                check_in_atten = zk_attendance.search(
                                    [('check_in', '=', atten_time), ('device_id_num', '=', user_id)])
                                check_out_atten = zk_attendance.search(
                                    [('check_out', '=', atten_time), ('device_id_num', '=', user_id)])
                                if not check_in_atten and not check_out_atten:
                                    zk_attendance.create({
                                        'employee_id': employee.id,
                                        'check_in': atten_time,
                                        'check_out': False,
                                        'device_id_num': user_id,
                                        'i_check': 'i',
                                    })
                                    hr_attendance.create({
                                        'employee_id': employee.id,
                                        'check_in': atten_time
                                    })
    
                conn.disconnect()
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
