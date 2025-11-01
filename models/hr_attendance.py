# models/hr_attendance.py
from odoo import models

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def _compute_overtime_hours(self):
        if self.env.context.get('no_overtime'):
            return
        return super()._compute_overtime_hours()