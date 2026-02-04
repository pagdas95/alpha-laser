"""
Analytics Views
Place this at: alpha/analytics/views.py (or in your visits app if you prefer)
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Q, F, Avg
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from alpha.visits.models import Visit
from alpha.appointments.models import Appointment
from alpha.clients.models import Client

# For Excel export
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False


class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Main analytics dashboard with charts and statistics"""
    template_name = 'analytics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get selected month from query params or default to current month
        selected_month = self.request.GET.get('month')
        if selected_month:
            try:
                selected_date = datetime.strptime(selected_month, '%Y-%m')
            except ValueError:
                selected_date = timezone.now()
        else:
            selected_date = timezone.now()
        
        # Calculate date range for the selected month
        start_date = selected_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
        
        context['selected_month'] = selected_date.strftime('%Y-%m')
        context['month_name'] = selected_date.strftime('%B %Y')
        
        # Get available months (last 12 months)
        context['available_months'] = self._get_available_months()
        
        # Basic statistics for the selected month
        context['stats'] = self._get_monthly_stats(start_date, end_date)
        
        return context
    
    def _get_available_months(self):
        """Get list of last 12 months for dropdown"""
        months = []
        current = timezone.now().replace(day=1)
        for i in range(12):
            months.append({
                'value': current.strftime('%Y-%m'),
                'label': current.strftime('%B %Y')
            })
            if current.month == 1:
                current = current.replace(year=current.year - 1, month=12)
            else:
                current = current.replace(month=current.month - 1)
        return months
    
    def _get_monthly_stats(self, start_date, end_date):
        """Calculate key statistics for the month"""
        
        # Filter visits and appointments for the month
        visits = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        )
        
        appointments = Appointment.objects.filter(
            start__gte=start_date,
            start__lt=end_date
        )
        
        # Calculate statistics
        stats = {
            'total_visits': visits.count(),
            'total_appointments': appointments.count(),
            'new_clients': Client.objects.filter(
                appointments__start__gte=start_date,
                appointments__start__lt=end_date
            ).distinct().count(),
            'revenue': visits.aggregate(
                total=Sum('charge_amount')
            )['total'] or Decimal('0.00'),
            'paid': visits.aggregate(
                total=Sum('paid_amount')
            )['total'] or Decimal('0.00'),
            'pending': Decimal('0.00'),
        }
        
        stats['pending'] = stats['revenue'] - stats['paid']
        
        # Payment status breakdown
        stats['fully_paid'] = visits.filter(
            paid_amount__gte=F('charge_amount')
        ).count()
        stats['partially_paid'] = visits.filter(
            paid_amount__gt=0,
            paid_amount__lt=F('charge_amount')
        ).count()
        stats['unpaid'] = visits.filter(paid_amount=0).count()
        
        # Appointment status breakdown
        stats['completed'] = appointments.filter(status='completed').count()
        stats['booked'] = appointments.filter(status='booked').count()
        stats['cancelled'] = appointments.filter(status='cancelled').count()
        stats['no_show'] = appointments.filter(status='no_show').count()
        
        return stats


class AnalyticsDataAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for chart data"""
    
    def get(self, request, *args, **kwargs):
        chart_type = request.GET.get('type', 'revenue')
        selected_month = request.GET.get('month')
        
        if selected_month:
            try:
                selected_date = datetime.strptime(selected_month, '%Y-%m')
            except ValueError:
                selected_date = timezone.now()
        else:
            selected_date = timezone.now()
        
        start_date = selected_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
        
        if chart_type == 'revenue':
            data = self._get_revenue_chart_data(start_date, end_date)
        elif chart_type == 'visits':
            data = self._get_visits_chart_data(start_date, end_date)
        elif chart_type == 'services':
            data = self._get_services_chart_data(start_date, end_date)
        elif chart_type == 'staff':
            data = self._get_staff_performance_data(start_date, end_date)
        elif chart_type == 'rooms':
            data = self._get_room_utilization_data(start_date, end_date)
        elif chart_type == 'machines':
            data = self._get_machine_utilization_data(start_date, end_date)
        elif chart_type == 'daily_revenue':
            data = self._get_daily_revenue_data(start_date, end_date)
        else:
            data = {'error': 'Invalid chart type'}
        
        return JsonResponse(data)
    
    def _get_revenue_chart_data(self, start_date, end_date):
        """Revenue vs Paid comparison"""
        visits = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        ).aggregate(
            revenue=Sum('charge_amount'),
            paid=Sum('paid_amount')
        )
        
        revenue = float(visits['revenue'] or 0)
        paid = float(visits['paid'] or 0)
        pending = revenue - paid
        
        return {
            'labels': ['Total Revenue', 'Paid', 'Pending'],
            'datasets': [{
                'label': 'Amount (€)',
                'data': [revenue, paid, pending],
                'backgroundColor': [
                    'rgba(81, 86, 190, 0.8)',
                    'rgba(42, 181, 125, 0.8)',
                    'rgba(255, 191, 83, 0.8)'
                ]
            }]
        }
    
    def _get_visits_chart_data(self, start_date, end_date):
        """Visits by payment status"""
        visits = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        )
        
        fully_paid = visits.filter(paid_amount__gte=F('charge_amount')).count()
        partially_paid = visits.filter(
            paid_amount__gt=0,
            paid_amount__lt=F('charge_amount')
        ).count()
        unpaid = visits.filter(paid_amount=0).count()
        
        return {
            'labels': ['Fully Paid', 'Partially Paid', 'Unpaid'],
            'datasets': [{
                'label': 'Number of Visits',
                'data': [fully_paid, partially_paid, unpaid],
                'backgroundColor': [
                    'rgba(42, 181, 125, 0.8)',
                    'rgba(255, 191, 83, 0.8)',
                    'rgba(253, 98, 94, 0.8)'
                ]
            }]
        }
    
    def _get_services_chart_data(self, start_date, end_date):
        """Top services by revenue"""
        services = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        ).values(
            'appointment__service__name'
        ).annotate(
            revenue=Sum('charge_amount'),
            count=Count('id')
        ).order_by('-revenue')[:10]
        
        return {
            'labels': [s['appointment__service__name'] for s in services],
            'datasets': [{
                'label': 'Revenue (€)',
                'data': [float(s['revenue']) for s in services],
                'backgroundColor': 'rgba(81, 86, 190, 0.8)',
            }]
        }
    
    def _get_staff_performance_data(self, start_date, end_date):
        """Staff performance - visits and revenue by staff member"""
        from django.contrib.auth import get_user_model
        from django.db.models import CharField, Value
        from django.db.models.functions import Coalesce, Concat
        
        User = get_user_model()
        
        # Build a flexible name field that works with different User models
        # Try to handle: name field, first_name/last_name, or just username
        staff_data = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        ).values('staff__id').annotate(
            visit_count=Count('id'),
            revenue=Sum('charge_amount')
        ).order_by('-visit_count')[:10]
        
        # Get staff names separately to handle different User model structures
        labels = []
        visit_counts = []
        revenues = []
        
        for s in staff_data:
            try:
                staff = User.objects.get(id=s['staff__id'])
                
                # Try different methods to get staff name
                if hasattr(staff, 'name') and staff.name:
                    name = staff.name
                elif hasattr(staff, 'get_full_name'):
                    full_name = staff.get_full_name()
                    name = full_name if full_name.strip() else str(staff)
                elif hasattr(staff, 'first_name') and hasattr(staff, 'last_name'):
                    if staff.first_name and staff.last_name:
                        name = f"{staff.first_name} {staff.last_name}"
                    elif staff.first_name:
                        name = staff.first_name
                    else:
                        name = staff.username
                else:
                    name = str(staff)
                
                labels.append(name)
                visit_counts.append(s['visit_count'])
                revenues.append(float(s['revenue']))
            except User.DoesNotExist:
                continue
        
        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Visits',
                    'data': visit_counts,
                    'backgroundColor': 'rgba(81, 86, 190, 0.8)',
                    'yAxisID': 'y',
                },
                {
                    'label': 'Revenue (€)',
                    'data': revenues,
                    'backgroundColor': 'rgba(42, 181, 125, 0.8)',
                    'yAxisID': 'y1',
                }
            ]
        }
    
    def _get_room_utilization_data(self, start_date, end_date):
        """Room utilization - appointments by room"""
        rooms = Appointment.objects.filter(
            start__gte=start_date,
            start__lt=end_date
        ).values(
            'room__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {
            'labels': [r['room__name'] for r in rooms],
            'datasets': [{
                'label': 'Appointments',
                'data': [r['count'] for r in rooms],
                'backgroundColor': [
                    'rgba(81, 86, 190, 0.8)',
                    'rgba(42, 181, 125, 0.8)',
                    'rgba(255, 191, 83, 0.8)',
                    'rgba(253, 98, 94, 0.8)',
                    'rgba(156, 39, 176, 0.8)',
                ]
            }]
        }
    
    def _get_machine_utilization_data(self, start_date, end_date):
        """Machine utilization - visits by machine"""
        machines = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date,
            machine__isnull=False
        ).values(
            'machine__name'
        ).annotate(
            count=Count('id'),
            revenue=Sum('charge_amount')
        ).order_by('-count')
        
        return {
            'labels': [m['machine__name'] for m in machines],
            'datasets': [
                {
                    'label': 'Visits',
                    'data': [m['count'] for m in machines],
                    'backgroundColor': 'rgba(81, 86, 190, 0.8)',
                },
                {
                    'label': 'Revenue (€)',
                    'data': [float(m['revenue']) for m in machines],
                    'backgroundColor': 'rgba(42, 181, 125, 0.8)',
                }
            ]
        }
    
    def _get_daily_revenue_data(self, start_date, end_date):
        """Daily revenue trend"""
        daily_data = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        ).annotate(
            day=TruncDay('appointment__start')
        ).values('day').annotate(
            revenue=Sum('charge_amount'),
            paid=Sum('paid_amount')
        ).order_by('day')
        
        return {
            'labels': [d['day'].strftime('%d %b') for d in daily_data],
            'datasets': [
                {
                    'label': 'Revenue',
                    'data': [float(d['revenue']) for d in daily_data],
                    'borderColor': 'rgba(81, 86, 190, 1)',
                    'backgroundColor': 'rgba(81, 86, 190, 0.1)',
                    'tension': 0.4
                },
                {
                    'label': 'Paid',
                    'data': [float(d['paid']) for d in daily_data],
                    'borderColor': 'rgba(42, 181, 125, 1)',
                    'backgroundColor': 'rgba(42, 181, 125, 0.1)',
                    'tension': 0.4
                }
            ]
        }


class ExportMonthlyReportView(LoginRequiredMixin, TemplateView):
    """Export monthly report to Excel"""
    
    def get(self, request, *args, **kwargs):
        if not EXCEL_AVAILABLE:
            return HttpResponse("Excel export not available. Install openpyxl.", status=500)
        
        selected_month = request.GET.get('month')
        if selected_month:
            try:
                selected_date = datetime.strptime(selected_month, '%Y-%m')
            except ValueError:
                selected_date = timezone.now()
        else:
            selected_date = timezone.now()
        
        start_date = selected_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
        
        # Create workbook
        wb = Workbook()
        
        # Create existing sheets
        self._create_summary_sheet(wb, start_date, end_date)
        self._create_visits_sheet(wb, start_date, end_date)
        self._create_services_sheet(wb, start_date, end_date)
        self._create_staff_sheet(wb, start_date, end_date)
        self._create_rooms_sheet(wb, start_date, end_date)
        self._create_machines_sheet(wb, start_date, end_date)
        
        # ✅ NEW: Create detailed appointment sheets
        self._create_cancelled_appointments_sheet(wb, start_date, end_date)
        self._create_no_show_appointments_sheet(wb, start_date, end_date)
        self._create_completed_appointments_sheet(wb, start_date, end_date)
        
        # Remove default sheet
        if 'Sheet' in wb.sheetnames:
            del wb['Sheet']
        
        # Prepare response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"Monthly_Report_{selected_date.strftime('%Y_%m')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response
    
    def _create_summary_sheet(self, wb, start_date, end_date):
        """Create summary statistics sheet"""
        ws = wb.active
        ws.title = "Summary"
        
        # Header styling
        header_fill = PatternFill(start_color="5156BE", end_color="5156BE", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        
        # Title
        ws['A1'] = f"Monthly Report - {start_date.strftime('%B %Y')}"
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:B1')
        
        # Statistics
        visits = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        )
        
        row = 3
        stats = [
            ('Total Visits', visits.count()),
            ('Total Revenue', f"€{visits.aggregate(Sum('charge_amount'))['charge_amount__sum'] or 0:.2f}"),
            ('Total Paid', f"€{visits.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0:.2f}"),
            ('Fully Paid Visits', visits.filter(paid_amount__gte=F('charge_amount')).count()),
            ('Partially Paid', visits.filter(paid_amount__gt=0, paid_amount__lt=F('charge_amount')).count()),
            ('Unpaid Visits', visits.filter(paid_amount=0).count()),
        ]
        
        for label, value in stats:
            ws[f'A{row}'] = label
            ws[f'B{row}'] = value
            ws[f'A{row}'].font = Font(bold=True)
            row += 1
        
        # Auto-size columns
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20
    
    def _create_visits_sheet(self, wb, start_date, end_date):
        """Create detailed visits sheet"""
        ws = wb.create_sheet("Visits Detail")
        
        # Headers
        headers = ['Date', 'Client', 'Service', 'Area', 'Staff', 'Charge', 'Paid', 'Balance', 'Payment Method']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="5156BE", end_color="5156BE", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        # Data
        visits = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        ).select_related(
            'appointment__client',
            'appointment__service',
            'staff'
        ).order_by('appointment__start')
        
        for row, visit in enumerate(visits, 2):
            # Get staff name using flexible method
            staff = visit.staff
            if hasattr(staff, 'name') and staff.name:
                staff_name = staff.name
            elif hasattr(staff, 'get_full_name'):
                full_name = staff.get_full_name()
                staff_name = full_name if full_name.strip() else staff.username
            else:
                staff_name = staff.username
            
            ws.cell(row=row, column=1, value=visit.appointment.start.strftime('%d/%m/%Y'))
            ws.cell(row=row, column=2, value=visit.appointment.client.full_name)
            ws.cell(row=row, column=3, value=visit.appointment.service.name)
            ws.cell(row=row, column=4, value=visit.area or '')
            ws.cell(row=row, column=5, value=staff_name)
            ws.cell(row=row, column=6, value=float(visit.charge_amount))
            ws.cell(row=row, column=7, value=float(visit.paid_amount))
            ws.cell(row=row, column=8, value=float(visit.charge_amount - visit.paid_amount))
            ws.cell(row=row, column=9, value=visit.get_payment_method_display() if visit.payment_method else '')
        
        # Auto-size columns
        for col in range(1, 10):
            ws.column_dimensions[get_column_letter(col)].width = 15
    
    def _create_services_sheet(self, wb, start_date, end_date):
        """Create services breakdown sheet"""
        ws = wb.create_sheet("Services Breakdown")
        
        # Headers
        headers = ['Service', 'Count', 'Total Revenue', 'Avg per Visit']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="5156BE", end_color="5156BE", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        # Data
        services = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        ).values(
            'appointment__service__name'
        ).annotate(
            count=Count('id'),
            revenue=Sum('charge_amount'),
            avg=Avg('charge_amount')
        ).order_by('-revenue')
        
        for row, service in enumerate(services, 2):
            ws.cell(row=row, column=1, value=service['appointment__service__name'])
            ws.cell(row=row, column=2, value=service['count'])
            ws.cell(row=row, column=3, value=float(service['revenue']))
            ws.cell(row=row, column=4, value=float(service['avg']))
        
        # Auto-size columns
        for col in range(1, 5):
            ws.column_dimensions[get_column_letter(col)].width = 20
    
    def _create_staff_sheet(self, wb, start_date, end_date):
        """Create staff performance sheet"""
        ws = wb.create_sheet("Staff Performance")
        
        # Headers
        headers = ['Staff Member', 'Total Visits', 'Total Revenue', 'Avg per Visit']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="5156BE", end_color="5156BE", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        # Data
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        staff_data = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        ).values('staff__id').annotate(
            visit_count=Count('id'),
            revenue=Sum('charge_amount'),
            avg=Avg('charge_amount')
        ).order_by('-visit_count')
        
        row = 2
        for staff_item in staff_data:
            try:
                staff = User.objects.get(id=staff_item['staff__id'])
                
                # Try different methods to get staff name
                if hasattr(staff, 'name') and staff.name:
                    name = staff.name
                elif hasattr(staff, 'get_full_name'):
                    full_name = staff.get_full_name()
                    name = full_name if full_name.strip() else str(staff)
                elif hasattr(staff, 'first_name') and hasattr(staff, 'last_name'):
                    if staff.first_name and staff.last_name:
                        name = f"{staff.first_name} {staff.last_name}"
                    elif staff.first_name:
                        name = staff.first_name
                    else:
                        name = staff.username
                else:
                    name = str(staff)
                
                ws.cell(row=row, column=1, value=name)
                ws.cell(row=row, column=2, value=staff_item['visit_count'])
                ws.cell(row=row, column=3, value=float(staff_item['revenue']))
                ws.cell(row=row, column=4, value=float(staff_item['avg']))
                row += 1
            except User.DoesNotExist:
                continue
        
        # Auto-size columns
        for col in range(1, 5):
            ws.column_dimensions[get_column_letter(col)].width = 20
    
    def _create_rooms_sheet(self, wb, start_date, end_date):
        """Create room utilization sheet"""
        ws = wb.create_sheet("Room Utilization")
        
        # Headers
        headers = ['Room Name', 'Total Appointments', 'Completed', 'Cancelled', 'No Show']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="5156BE", end_color="5156BE", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        # Data
        rooms_data = Appointment.objects.filter(
            start__gte=start_date,
            start__lt=end_date
        ).values('room__name').annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            no_show=Count('id', filter=Q(status='no_show'))
        ).order_by('-total')
        
        for row, room in enumerate(rooms_data, 2):
            ws.cell(row=row, column=1, value=room['room__name'])
            ws.cell(row=row, column=2, value=room['total'])
            ws.cell(row=row, column=3, value=room['completed'])
            ws.cell(row=row, column=4, value=room['cancelled'])
            ws.cell(row=row, column=5, value=room['no_show'])
        
        # Auto-size columns
        for col in range(1, 6):
            ws.column_dimensions[get_column_letter(col)].width = 20
    
    def _create_machines_sheet(self, wb, start_date, end_date):
        """Create machine utilization sheet"""
        ws = wb.create_sheet("Machine Utilization")
        
        # Headers
        headers = ['Machine Name', 'Total Visits', 'Total Revenue', 'Avg per Visit']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="5156BE", end_color="5156BE", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        # Data
        machines_data = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date,
            machine__isnull=False
        ).values('machine__name').annotate(
            visit_count=Count('id'),
            revenue=Sum('charge_amount'),
            avg=Avg('charge_amount')
        ).order_by('-visit_count')
        
        for row, machine in enumerate(machines_data, 2):
            ws.cell(row=row, column=1, value=machine['machine__name'])
            ws.cell(row=row, column=2, value=machine['visit_count'])
            ws.cell(row=row, column=3, value=float(machine['revenue']))
            ws.cell(row=row, column=4, value=float(machine['avg']))
        
        # Auto-size columns
        for col in range(1, 5):
            ws.column_dimensions[get_column_letter(col)].width = 20
    
    # ========================================
    # ✅ NEW: 3 DETAILED APPOINTMENT SHEETS
    # ========================================
    
    def _create_cancelled_appointments_sheet(self, wb, start_date, end_date):
        """Create detailed list of cancelled appointments with client names"""
        ws = wb.create_sheet("Cancelled Appointments")
        
        # Headers
        headers = [
            'Date', 'Time', 'Client Name', 'Service', 'Staff', 
            'Room', 'Duration', 'Price', 'Cancellation Reason'
        ]
        
        # Style headers (RED for cancelled)
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="DC3545", end_color="DC3545", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
        
        # Get cancelled appointments with related data
        cancelled_appointments = Appointment.objects.filter(
            start__gte=start_date,
            start__lt=end_date,
            status='cancelled'
        ).select_related(
            'client', 'service', 'staff', 'room'
        ).order_by('start')
        
        # Write data
        row = 2
        for apt in cancelled_appointments:
            # Get staff name
            if hasattr(apt.staff, 'name') and apt.staff.name:
                staff_name = apt.staff.name
            else:
                staff_name = apt.staff.username
            
            # Calculate duration
            duration_minutes = int((apt.end - apt.start).total_seconds() / 60)
            
            # Get price
            price = float(apt.price_override) if apt.price_override else float(apt.service.default_price)
            
            ws.cell(row=row, column=1, value=apt.start.strftime('%d/%m/%Y'))
            ws.cell(row=row, column=2, value=apt.start.strftime('%H:%M'))
            ws.cell(row=row, column=3, value=apt.client.full_name)
            ws.cell(row=row, column=4, value=apt.service.name)
            ws.cell(row=row, column=5, value=staff_name)
            ws.cell(row=row, column=6, value=apt.room.name)
            ws.cell(row=row, column=7, value=f"{duration_minutes} min")
            ws.cell(row=row, column=8, value=price)
            ws.cell(row=row, column=9, value=apt.notes or "")
            
            # Format price cell
            ws.cell(row=row, column=8).number_format = '€#,##0.00'
            
            row += 1
        
        # Add total count
        total_row = row + 1
        ws.cell(row=total_row, column=1, value="TOTAL:")
        ws.cell(row=total_row, column=1).font = Font(bold=True)
        ws.cell(row=total_row, column=3, value=f"{cancelled_appointments.count()} cancelled appointments")
        ws.cell(row=total_row, column=3).font = Font(bold=True)
        
        # Calculate total lost revenue
        total_lost = sum(
            float(apt.price_override) if apt.price_override else float(apt.service.default_price)
            for apt in cancelled_appointments
        )
        ws.cell(row=total_row, column=7, value="Lost Revenue:")
        ws.cell(row=total_row, column=7).font = Font(bold=True)
        ws.cell(row=total_row, column=8, value=total_lost)
        ws.cell(row=total_row, column=8).font = Font(bold=True, color="DC3545")
        ws.cell(row=total_row, column=8).number_format = '€#,##0.00'
        
        # Auto-size columns
        column_widths = {
            'A': 12, 'B': 10, 'C': 25, 'D': 30, 'E': 20,
            'F': 15, 'G': 12, 'H': 12, 'I': 40,
        }
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width
        
        # Freeze header row
        ws.freeze_panes = 'A2'
    
    def _create_no_show_appointments_sheet(self, wb, start_date, end_date):
        """Create detailed list of no-show appointments with client names and phone"""
        ws = wb.create_sheet("No-Show Appointments")
        
        # Headers
        headers = [
            'Date', 'Time', 'Client Name', 'Client Phone', 'Service', 
            'Staff', 'Room', 'Price', 'Notes'
        ]
        
        # Style headers (ORANGE for no-show)
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="FFC107", end_color="FFC107", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
        
        # Get no-show appointments with related data
        no_show_appointments = Appointment.objects.filter(
            start__gte=start_date,
            start__lt=end_date,
            status='no_show'
        ).select_related(
            'client', 'service', 'staff', 'room'
        ).order_by('start')
        
        # Write data
        row = 2
        for apt in no_show_appointments:
            # Get staff name
            if hasattr(apt.staff, 'name') and apt.staff.name:
                staff_name = apt.staff.name
            else:
                staff_name = apt.staff.username
            
            # Get price
            price = float(apt.price_override) if apt.price_override else float(apt.service.default_price)
            
            ws.cell(row=row, column=1, value=apt.start.strftime('%d/%m/%Y'))
            ws.cell(row=row, column=2, value=apt.start.strftime('%H:%M'))
            ws.cell(row=row, column=3, value=apt.client.full_name)
            ws.cell(row=row, column=4, value=apt.client.phone)
            ws.cell(row=row, column=5, value=apt.service.name)
            ws.cell(row=row, column=6, value=staff_name)
            ws.cell(row=row, column=7, value=apt.room.name)
            ws.cell(row=row, column=8, value=price)
            ws.cell(row=row, column=9, value=apt.notes or "")
            
            # Format price cell
            ws.cell(row=row, column=8).number_format = '€#,##0.00'
            
            # Highlight client phone for easy follow-up
            ws.cell(row=row, column=4).fill = PatternFill(
                start_color="FFF3CD", end_color="FFF3CD", fill_type="solid"
            )
            
            row += 1
        
        # Add total count
        total_row = row + 1
        ws.cell(row=total_row, column=1, value="TOTAL:")
        ws.cell(row=total_row, column=1).font = Font(bold=True)
        ws.cell(row=total_row, column=3, value=f"{no_show_appointments.count()} no-show appointments")
        ws.cell(row=total_row, column=3).font = Font(bold=True)
        
        # Calculate total lost revenue
        total_lost = sum(
            float(apt.price_override) if apt.price_override else float(apt.service.default_price)
            for apt in no_show_appointments
        )
        ws.cell(row=total_row, column=7, value="Lost Revenue:")
        ws.cell(row=total_row, column=7).font = Font(bold=True)
        ws.cell(row=total_row, column=8, value=total_lost)
        ws.cell(row=total_row, column=8).font = Font(bold=True, color="FFC107")
        ws.cell(row=total_row, column=8).number_format = '€#,##0.00'
        
        # Auto-size columns
        column_widths = {
            'A': 12, 'B': 10, 'C': 25, 'D': 15, 'E': 30,
            'F': 20, 'G': 15, 'H': 12, 'I': 40,
        }
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width
        
        # Freeze header row
        ws.freeze_panes = 'A2'
    
    def _create_completed_appointments_sheet(self, wb, start_date, end_date):
        """Create detailed list of completed appointments with payment details"""
        ws = wb.create_sheet("Completed Appointments")
        
        # Headers
        headers = [
            'Date', 'Time', 'Client Name', 'Service', 'Staff', 
            'Room', 'Machine', 'Charged', 'Paid', 'Balance', 'Payment Status'
        ]
        
        # Style headers (GREEN for completed)
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="28A745", end_color="28A745", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
        
        # Get completed appointments with visits
        completed_appointments = Appointment.objects.filter(
            start__gte=start_date,
            start__lt=end_date,
            status='completed'
        ).select_related(
            'client', 'service', 'staff', 'room'
        ).prefetch_related('visit').order_by('start')
        
        # Write data
        row = 2
        total_charged = 0
        total_paid = 0
        
        for apt in completed_appointments:
            # Get staff name
            if hasattr(apt.staff, 'name') and apt.staff.name:
                staff_name = apt.staff.name
            else:
                staff_name = apt.staff.username
            
            # Get visit data if exists
            if hasattr(apt, 'visit'):
                visit = apt.visit
                charged = float(visit.charge_amount)
                paid = float(visit.paid_amount)
                balance = charged - paid
                
                # Determine payment status
                if paid >= charged:
                    payment_status = "Fully Paid"
                elif paid > 0:
                    payment_status = "Partially Paid"
                else:
                    payment_status = "Unpaid"
                
                machine_name = visit.machine.name if visit.machine else ""
            else:
                # No visit record
                price = float(apt.price_override) if apt.price_override else float(apt.service.default_price)
                charged = price
                paid = 0
                balance = charged
                payment_status = "No Visit Record"
                machine_name = ""
            
            ws.cell(row=row, column=1, value=apt.start.strftime('%d/%m/%Y'))
            ws.cell(row=row, column=2, value=apt.start.strftime('%H:%M'))
            ws.cell(row=row, column=3, value=apt.client.full_name)
            ws.cell(row=row, column=4, value=apt.service.name)
            ws.cell(row=row, column=5, value=staff_name)
            ws.cell(row=row, column=6, value=apt.room.name)
            ws.cell(row=row, column=7, value=machine_name)
            ws.cell(row=row, column=8, value=charged)
            ws.cell(row=row, column=9, value=paid)
            ws.cell(row=row, column=10, value=balance)
            ws.cell(row=row, column=11, value=payment_status)
            
            # Format currency cells
            ws.cell(row=row, column=8).number_format = '€#,##0.00'
            ws.cell(row=row, column=9).number_format = '€#,##0.00'
            ws.cell(row=row, column=10).number_format = '€#,##0.00'
            
            # Color-code payment status
            status_cell = ws.cell(row=row, column=11)
            if payment_status == "Fully Paid":
                status_cell.fill = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
                status_cell.font = Font(color="155724")
            elif payment_status == "Partially Paid":
                status_cell.fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
                status_cell.font = Font(color="856404")
            elif payment_status == "Unpaid":
                status_cell.fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
                status_cell.font = Font(color="721C24")
            
            total_charged += charged
            total_paid += paid
            
            row += 1
        
        # Add totals row
        total_row = row + 1
        ws.cell(row=total_row, column=1, value="TOTALS:")
        ws.cell(row=total_row, column=1).font = Font(bold=True)
        ws.cell(row=total_row, column=3, value=f"{completed_appointments.count()} completed appointments")
        ws.cell(row=total_row, column=3).font = Font(bold=True)
        
        ws.cell(row=total_row, column=7, value="Total Charged:")
        ws.cell(row=total_row, column=7).font = Font(bold=True)
        ws.cell(row=total_row, column=8, value=total_charged)
        ws.cell(row=total_row, column=8).font = Font(bold=True)
        ws.cell(row=total_row, column=8).number_format = '€#,##0.00'
        
        ws.cell(row=total_row + 1, column=7, value="Total Paid:")
        ws.cell(row=total_row + 1, column=7).font = Font(bold=True)
        ws.cell(row=total_row + 1, column=8, value=total_paid)
        ws.cell(row=total_row + 1, column=8).font = Font(bold=True, color="28A745")
        ws.cell(row=total_row + 1, column=8).number_format = '€#,##0.00'
        
        ws.cell(row=total_row + 2, column=7, value="Outstanding:")
        ws.cell(row=total_row + 2, column=7).font = Font(bold=True)
        ws.cell(row=total_row + 2, column=8, value=total_charged - total_paid)
        ws.cell(row=total_row + 2, column=8).font = Font(bold=True, color="DC3545")
        ws.cell(row=total_row + 2, column=8).number_format = '€#,##0.00'
        
        # Auto-size columns
        column_widths = {
            'A': 12, 'B': 10, 'C': 25, 'D': 30, 'E': 20,
            'F': 15, 'G': 20, 'H': 12, 'I': 12, 'J': 12, 'K': 15,
        }
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width
        
        # Freeze header row
        ws.freeze_panes = 'A2'


class AnalyticsDebugView(LoginRequiredMixin, TemplateView):
    """Debug view to help troubleshoot staff, room, and machine data"""
    template_name = 'analytics/debug.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get recent visits
        context['recent_visits'] = Visit.objects.select_related(
            'staff', 'appointment', 'machine'
        ).order_by('-created_at')[:10]
        
        # Get User model field information
        user_fields = []
        for field in User._meta.get_fields():
            try:
                user_fields.append({
                    'name': field.name,
                    'type': field.__class__.__name__
                })
            except:
                pass
        context['user_fields'] = user_fields
        
        # Test staff performance query
        from datetime import datetime, timedelta
        end_date = timezone.now()
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        staff_data = Visit.objects.filter(
            appointment__start__gte=start_date,
            appointment__start__lt=end_date
        ).values('staff__id').annotate(
            visit_count=Count('id'),
            revenue=Sum('charge_amount')
        ).order_by('-visit_count')[:10]
        
        staff_stats = []
        for s in staff_data:
            try:
                staff = User.objects.get(id=s['staff__id'])
                
                # Try different methods to get staff name
                if hasattr(staff, 'name') and staff.name:
                    name = staff.name
                elif hasattr(staff, 'get_full_name'):
                    full_name = staff.get_full_name()
                    name = full_name if full_name.strip() else str(staff)
                else:
                    name = str(staff)
                
                staff_stats.append({
                    'name': name,
                    'visit_count': s['visit_count'],
                    'revenue': s['revenue']
                })
            except User.DoesNotExist:
                continue
        
        context['staff_stats'] = staff_stats
        
        # Get recent appointments
        context['recent_appointments'] = Appointment.objects.select_related(
            'room'
        ).order_by('-created_at')[:10]
        
        # Get visits with machines
        context['visits_with_machines'] = Visit.objects.filter(
            machine__isnull=False
        ).select_related('machine').order_by('-created_at')[:10]
        
        # Summary statistics
        context['total_visits'] = Visit.objects.count()
        context['visits_with_staff'] = Visit.objects.filter(staff__isnull=False).count()
        context['visits_with_machines_count'] = Visit.objects.filter(machine__isnull=False).count()
        context['total_appointments'] = Appointment.objects.count()
        context['unique_staff'] = Visit.objects.values('staff').distinct().count()
        context['unique_rooms'] = Appointment.objects.values('room').distinct().count()
        context['unique_machines'] = Visit.objects.filter(machine__isnull=False).values('machine').distinct().count()
        
        return context