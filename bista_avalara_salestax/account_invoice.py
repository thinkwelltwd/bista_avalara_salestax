# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
#import string
from openerp import fields as new_fields
from openerp import api
from openerp.osv import fields,osv
#from openerp.osv import osv
from openerp import models
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


def get_address_for_tax(self, cr, uid, ids, context=None):
    """ partner address, on which avalara tax will calculate  """
    for inv_obj in self.pool.get('account.invoice').browse(cr, uid, ids, context):
        if inv_obj.origin:
            a = inv_obj.origin
            
            if len(a.split(':')) > 1:
                so_origin = a.split(':')[1]
            else:
                so_origin = a.split(':')[0]
                
            sale_ids = self.pool.get('sale.order').search(cr, uid, [('name','=',so_origin)], context=context)
            if not sale_ids:
                inv_ids = self.pool.get('account.invoice').search(cr, uid, [('number','=',so_origin)], context=context)  
                for invoice in self.pool.get('account.invoice').browse(cr, uid, inv_ids, context):
                    return invoice.partner_id.id
                else:
                    return inv_obj.partner_id.id                
                
                
            for order in self.pool.get('sale.order').browse(cr, uid, sale_ids, context):
                if order.tax_add_invoice:
                    return order.partner_invoice_id.id
                elif order.tax_add_shipping:
                    return order.partner_shipping_id.id
                elif order.tax_add_default:
                    return order.partner_id.id
                else:
                    raise osv.except_osv(_('AvaTax: Warning !'), _('Please select address for avalara tax'))
        else:
            return inv_obj.partner_id.id

def get_origin_address_for_tax(self, cr, uid, ids, context=None):
    """ partner address, on which avalara tax will calculate  """
    sale_ids = pick_ids = False
    for inv_obj in self.pool.get('account.invoice').browse(cr, uid, ids, context):
        if not inv_obj.warehouse_id:
            if inv_obj.origin:
                a = inv_obj.origin

                if len(a.split(':')) > 1:
                    so_origin = a.split(':')[1]
                else:
                    so_origin = a.split(':')[0]
                
                sale_obj = self.pool.get('sale.order')    
                pick_obj = self.pool.get('stock.picking')
                sale_ids = sale_obj.search(cr, uid, [('name','=',so_origin)], context=context)
                pick_ids = pick_obj.search(cr, uid, [('name','=',so_origin)])
                if not sale_ids:
                    inv_ids = self.pool.get('account.invoice').search(cr, uid, [('number','=', so_origin)], context=context)  
                    if inv_ids:
                        for invoice in self.pool.get('account.invoice').browse(cr, uid, inv_ids, context):
                            if invoice.warehouse_id:
                                return invoice.warehouse_id.partner_id.id
                            else:
                                return inv_obj.partner_id.id
                    elif pick_ids:
                        pick_type = pick_obj.browse(cr, uid, pick_ids[0], context=context).picking_type_id
                        return pick_type and pick_type.warehouse_id and pick_type.warehouse_id.partner_id and pick_type.warehouse_id.partner_id.id or False 
                else:
                    for order in sale_obj.browse(cr, uid, sale_ids, context):
                        if order.warehouse_id:
                            return order.warehouse_id.partner_id.id
                        else:
                            return inv_obj.partner_id.id
            else:
                return inv_obj.company_id and inv_obj.company_id.partner_id and inv_obj.company_id.partner_id.id
        else:
            return inv_obj.warehouse_id.partner_id and inv_obj.warehouse_id.partner_id.id or False   

def get_origin_tax_date(self, cr, uid, ids, context=None):
    """ partner address, on which avalara tax will calculate  """
    for inv_obj in self.pool.get('account.invoice').browse(cr, uid, ids, context):
        if inv_obj.origin:
            a = inv_obj.origin
            
            if len(a.split(':')) > 1:
                inv_origin = a.split(':')[1]
            else:
                inv_origin = a.split(':')[0]
                
            inv_ids = self.pool.get('account.invoice').search(cr, uid, [('number','=',inv_origin)], context=context)  
            for invoice in self.pool.get('account.invoice').browse(cr, uid, inv_ids, context):
                if invoice.date_invoice:
                    return invoice.date_invoice
                else:
                    return inv_obj.date_invoice                                 

        else:
            return False          

class account_invoice(osv.osv):
    """Inherit to implement the tax calculation using avatax API"""
    _inherit = "account.invoice"

    def onchange_partner_id(self, cr, uid, ids, type, partner_id, date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False,context ={}): 
        res = super(account_invoice, self).onchange_partner_id(cr, uid, ids, type, partner_id,\
            date_invoice, payment_term, partner_bank_id, company_id)
        
        res_obj = self.pool.get('res.partner').browse(cr, uid, partner_id)
        addr = self.pool.get('res.partner').browse(cr, uid, res['value'] and partner_id)        
        res['value']['exemption_code'] = res_obj.exemption_number or ''
        res['value']['exemption_code_id'] = res_obj.exemption_code_id.id or None
        #res['value']['tax_add_shipping'] = True
        res['value']['shipping_address'] = str((addr.name  or '')+ '\n'+(addr.street or '')+ '\n'+(addr.city and addr.city+', ' or ' ')+(addr.state_id and addr.state_id.name or '')+ ' '+(addr.zip or '')+'\n'+(addr.country_id and addr.country_id.name or ''))        
        if res_obj.validation_method:res['value']['is_add_validate'] = True
        else:res['value']['is_add_validate'] = False
        return res
            
    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
     
        val={}      
        if warehouse_id:
            warehouse = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
            if warehouse.company_id:
                val['company_id'] = warehouse.company_id.id
            if warehouse.code:
                val['location_code'] = warehouse.code

        return {'value': val}  
    
#    @api.one
#    @api.depends(
#        'state', 'currency_id', 'invoice_line.price_subtotal',
#        'shipping_amt',
#        'move_id.line_id.account_id.type',
#        'move_id.line_id.amount_residual',
#        # Fixes the fact that move_id.line_id.amount_residual, being not stored and old API, doesn't trigger recomputation
#        'move_id.line_id.reconcile_id',
#        'move_id.line_id.amount_residual_currency',
#        'move_id.line_id.currency_id',
#        'move_id.line_id.reconcile_partial_id.line_partial_ids.invoice.type',
#    )
#    # An invoice's residual amount is the sum of its unreconciled move lines and,
#    # for partially reconciled move lines, their residual amount divided by the
#    # number of times this reconciliation is used in an invoice (so we split
#    # the residual amount between all invoice)
#    def _compute_residual(self):
#        super(account_invoice, self)._compute_residual()
##        print"self.residualself.residual",self.residual
##        self.residual = self.residual + self.shipping_amt        
##        self.residual = max(self.residual, 0.0)
        
    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount','shipping_amt')
    def _compute_amount(self):
        #TODO: Need logic for Additional Discount seperately.
        #AmountAll is not used anymore in Invoice.
        shipping_amt = 0
        for ship_line in self.shipping_lines:
            shipping_amt += ship_line.shipping_cost

        def cur_round(value):
                """Round value according to currency."""
                return self.currency_id.round(value)
                                   
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        self.shipping_amt = shipping_amt
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.amount_total = self.shipping_amt + self.amount_tax + self.amount_untaxed
        
#    def _amount_all(self, cr, uid, ids, name, args, context=None):
#        res = {}
#        for invoice in self.browse(cr, uid, ids, context=context):
#            res[invoice.id] = {
#                'amount_untaxed': 0.0,
#                'amount_tax': 0.0,
#                'amount_total': 0.0,
#                'shipping_amt': 0.0,
#            }
#            for line in invoice.invoice_line:
#                res[invoice.id]['amount_untaxed'] += line.price_subtotal
#            for line in invoice.tax_line:
#                res[invoice.id]['amount_tax'] += line.amount                
#            for ship_line in invoice.shipping_lines:
#                res[invoice.id]['shipping_amt'] += ship_line.shipping_cost
#
#            res[invoice.id]['amount_total'] = res[invoice.id]['amount_untaxed'] + res[invoice.id]['amount_tax'] + res[invoice.id]['shipping_amt']                
#            print"res",res
#            #res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']        
#            return res      
    
    def _get_invoice_tax(self, cr, uid, ids, context=None):
        #invoice = self.pool.get('account.invoice')
        #return super(account_invoice, invoice)._get_invoice_tax(cr, uid, ids, context=context)
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()
    
    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()         
        '''     invoice = self.pool.get('account.invoice')
        return super(account_invoice, invoice)._get_invoice_line(cr, uid, ids, context=context)
        
'''
   
    
    def _get_invoice_from_line(self, cr, uid, ids, context=None):
        invoice = self.pool.get('account.invoice')
        return super(account_invoice, invoice)._get_invoice_from_line(cr, uid, ids, context=context)
    
    def _total_weight_net(self, cr, uid, ids, field_name, arg, context):
        """Compute the total net weight of the given Invoice."""
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            result[invoice.id] = 0.0
            for line in invoice.invoice_line:
                if line.product_id:
                    result[invoice.id] += line.weight_net or 0.0
        return result
    
    def _get_invoice(self, cr, uid, ids, context={}):
        """Get the invoice ids of the given Invoice Lines."""
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids,
            context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def create(self, cr, uid, vals, context=None):
        if vals.get('partner_id', False):
            res_obj = self.pool.get('res.partner').browse(cr, uid, vals['partner_id'], context=context)
            if 'exemption_code' in vals:
                vals['exemption_code'] = vals['exemption_code']
            else:
                vals['exemption_code'] = res_obj.exemption_number or ''
            if 'exemption_code_id' in vals:
                vals['exemption_code_id'] = vals['exemption_code_id']
            else:
                vals['exemption_code_id'] = res_obj.exemption_code_id and res_obj.exemption_code_id.id or False

            
            sale_obj = self.pool.get('sale.order')    
            pick_obj = self.pool.get('stock.picking')
            sale_ids = sale_obj.search(cr, uid, [('name','=',vals.get('origin',''))])
            pick_ids = pick_obj.search(cr, uid, [('name','=',vals.get('origin',''))])
            if sale_ids:
                sale_order = sale_obj.browse(cr, uid, sale_ids[0], context=context)
                if 'warehouse_id' in sale_order:
                    vals['warehouse_id'] = sale_order.warehouse_id and sale_order.warehouse_id.id or False
                    vals['location_code'] = sale_order.warehouse_id and sale_order.warehouse_id.code or False
                if pick_ids:
                    pick_type = pick_obj.browse(cr, uid, pick_ids[0], context=context).picking_type_id
                    vals['warehouse_id'] = pick_type and pick_type.warehouse_id and pick_type.warehouse_id.id or False
                    vals['location_code'] = pick_type and pick_type.warehouse_id and pick_type.warehouse_id.code or False
            if res_obj.validation_method:vals['is_add_validate'] = True
            addr = self.pool.get('res.partner').browse(cr, uid, 'partner_invoice_id' in vals and vals['partner_invoice_id'] or vals['partner_id'], context=context)
            vals['shipping_address'] = str(addr.name+ '\n'+(addr.street or '')+ '\n'+(addr.city and addr.city+', ' or ' ')+(addr.state_id and addr.state_id.name or '')+ ' '+(addr.zip or '')+'\n'+(addr.country_id and addr.country_id.name or ''))
        
        return super(account_invoice, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        if 'partner_id' in vals:
            res_obj = self.pool.get('res.partner').browse(cr, uid, vals['partner_id'], context=context)
            if 'exemption_code' in vals:
                vals['exemption_code'] = vals['exemption_code']
            else:
                vals['exemption_code'] = res_obj.exemption_number or ''
            if 'exemption_code_id' in vals:
                vals['exemption_code_id'] = vals['exemption_code_id']
            else:
                vals['exemption_code_id'] = res_obj.exemption_code_id and res_obj.exemption_code_id.id or False
            if res_obj.validation_method:
                vals['is_add_validate'] = True
            else:
                vals['is_add_validate'] = False
            addr = self.pool.get('res.partner').browse(cr, uid, 'partner_invoice_id' in vals and vals['partner_invoice_id'] or vals['partner_id'], context=context)
            vals['shipping_address'] = str(addr.name+ '\n'+(addr.street or '')+ '\n'+(addr.city and addr.city+', ' or ' ')+(addr.state_id and addr.state_id.name or '')+ ' '+(addr.zip or '')+'\n'+(addr.country_id and addr.country_id.name or ''))    
                
        if 'tax_add_default' in vals: vals['tax_add_default'] = vals['tax_add_default']
        if 'tax_add_invoice' in vals: vals['tax_add_invoice'] = vals['tax_add_invoice']
        if 'tax_add_shipping' in vals: vals['tax_add_shipping'] = vals['tax_add_shipping']
        if 'shipping_address' in vals: vals['shipping_address'] = vals['shipping_address']
        
        return super(account_invoice, self).write(cr, uid, ids, vals, context=context)        
    
    amount_untaxed = new_fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = new_fields.Float(string='Tax', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    amount_total = new_fields.Float(string='Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    shipping_amt = new_fields.Float(string='Shipping Cost', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
#    residual = new_fields.Float(string='Balance', digits=dp.get_precision('Account'),
#        compute='_compute_residual', store=True,
#        help="Remaining amount due.")
        
    _columns = {
        'invoice_doc_no': fields.char('Source/Ref Invoice No', size=32, readonly=True, states={'draft':[('readonly',False)]}, help="Reference of the invoice"),
        'invoice_date': fields.date('Invoice Date', readonly=True),
        'is_add_validate': fields.boolean('Address validated',),
        
#        'shipping_amt': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Shipping Cost',
#            store={
#                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['shipping_lines'], -10),
#                'account.invoice.tax': (_get_invoice_tax, None, -10),
#                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], -10),
#            }, multi='all'),
#        'amount_total': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Total',
#            store={
#                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line', 'shipping_lines','shipping_amt'], -10),
#                'account.invoice.tax': (_get_invoice_tax, None, -10),
#                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], -10),
#            }, multi='all'),
#        'amount_untaxed': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Subtotal',
#            store={
#                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line', 'shipping_lines','shipping_amt'], -10),
#                'account.invoice.tax': (_get_invoice_tax, None, -10),
#                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], -10),
#            }, multi='all'),
#        
#        'amount_tax': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Tax',
#            store={
#                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line', 'shipping_lines','shipping_amt'], -10),
#                'account.invoice.tax': (_get_invoice_tax, None, -10),
#                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], -10),
#            }, multi='all'),
#            
        'total_weight_net': fields.function(_total_weight_net, method=True,
            readonly=True, string='Total Net Weight',
            help="The cumulated net weight of all the invoice lines.",
            store={
                # Low priority to compute this before fields in other modules
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                     ['invoice_line'], 10),
                'account.invoice.line': (_get_invoice,
                     ['quantity', 'product_id'], 10),
            },
        ),
        'exemption_code': fields.char('Exemption Number', help="It show the customer exemption number"),
        'exemption_code_id': fields.many2one('exemption.code', 'Exemption Code', help="It show the customer exemption code"),
        'shipping_lines': fields.one2many('shipping.order.line','invoice_ship_id', 'AvaTax Shipping Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'tax_add_default': fields.boolean('Default Address', readonly=True, states={'draft':[('readonly',False)]}),
        'tax_add_invoice': fields.boolean('Invoice Address', readonly=True, states={'draft':[('readonly',False)]}),
        'tax_add_shipping': fields.boolean('Delivery Address', readonly=True, states={'draft':[('readonly',False)]}),
        'shipping_add_id': fields.many2one('res.partner', 'Tax Address', change_default=True, track_visibility='always'),
        'shipping_address': fields.text('Tax Address'),
        'location_code': fields.char('Location code', size=128, readonly=True, states={'draft':[('readonly',False)]}),  
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'partner_invoice_id': fields.many2one('res.partner', 'Invoice Address', readonly=True, required=True, states={'draft': [('readonly', False)]}, help="Invoice address for current sales order."),
        'partner_shipping_id': fields.many2one('res.partner', 'Delivery Address', readonly=True, required=True, states={'draft': [('readonly', False)]}, help="Delivery address for current sales order."),
                
    }
    
    _defaults = {
        'tax_add_invoice': True,
        'partner_invoice_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['invoice'])['invoice'],
        'partner_shipping_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['delivery'])['delivery'],        
        
        }


    def finalize_invoice_move_lines(self, move_lines):
        
        """After validate invoice create finalize invoice move lines with shipping amount
        and also manage the debit and credit balance """
        
        #odoo8 api Adapt
        invoice_browse = self
        recs = self.env['account.move.line']
        uid = recs.env.uid
        cr = recs.env.cr

        flag = False
        account = False

        move_lines = super(account_invoice, self).finalize_invoice_move_lines(move_lines)
        if invoice_browse.type == "out_refund":
            account = invoice_browse.account_id.id
        else:
            if invoice_browse.shipping_lines:
                for ship_line in invoice_browse.shipping_lines:
                    flag = True
                    account = ship_line.sale_account_id.id

        if flag and invoice_browse.shipping_amt:
            lines1={
                    'analytic_account_id' :  False,
                    'tax_code_id' :  False,
                    'analytic_lines' :  [],
                    'tax_amount' :  invoice_browse.shipping_amt,
                    'name' :  'Shipping Charge',
                    'ref' : '',
                    'currency_id' :  False,
                    'credit' :  invoice_browse.shipping_amt,
                    'product_id' :  False,
                    'date_maturity' : False,
                    'debit' : False,
                    'date' : time.strftime("%Y-%m-%d"),
                    'amount_currency' : 0,
                    'product_uom_id' :  False,
                    'quantity' : 1,
                    'partner_id' : invoice_browse.partner_id.id,
                    'account_id' : account,}
            
            move_lines.append((0,0,lines1))
            # Retrieve the existing debit line if one exists
            has_entry = False
            for move_line in move_lines:
                
                journal_entry = move_line[2]
                if journal_entry['account_id'] == invoice_browse.account_id.id:
                   journal_entry['debit'] += invoice_browse.shipping_amt
                   has_entry = True
                   break
            # If debit line does not exist create one. Generally this condition will not happen. Just a fail-safe option    
            if not has_entry:
                lines2={
                        'analytic_account_id' :  False,
                        'tax_code_id' :  False,
                        'analytic_lines' :  [],
                        'tax_amount' :  False,
                        'name' :  '/',
                        'ref' : '',
                        'currency_id' :  False,
                        'credit' :  False,
                        'product_id' :  False,
                        'date_maturity' : False,
                        'debit' : invoice_browse.shipping_amt,
                        'date' : time.strftime("%Y-%m-%d"),
                        'amount_currency' : 0,
                        'product_uom_id' :  False,
                        'quantity' : 1,
                        'partner_id' : invoice_browse.partner_id.id,
                        'account_id' : invoice_browse.journal_id.default_debit_account_id.id,}
            
                move_lines.append((0,0,lines2))
        return move_lines    
    
    
    def confirm_paid(self, cr, uid, ids, context=None):
        """After validation invoice will pay by payment register and also committed the avalara invoice record"""
        if context is None:
            context = {}
        avatax_config_obj = self.pool.get('avalara.salestax')
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
        account_tax_obj = self.pool.get('account.tax')
#        partner_obj = self.pool.get('res.partner')
        
        # Bypass reporting
        if avatax_config and avatax_config.disable_tax_reporting:
            return True        
        
        for invoice in self.browse(cr, uid, ids, context=context):
#            c_code = partner_obj.browse(cr, uid, invoice.partner_id.id).country_id.code or False
#            cs_code = []        #Countries where Avalara address validation is enabled
#            for c_brw in avatax_config.country_ids:
#                cs_code.append(str(c_brw.code))
            if avatax_config and not avatax_config.disable_tax_calculation and invoice.type in ['out_invoice','out_refund']:
#            and c_code in cs_code:
                shipping_add_id = get_address_for_tax(self, cr, uid, [invoice.id], context)
                shipping_add_origin_id = get_origin_address_for_tax(self, cr, uid, [invoice.id], context)
                tax_date = get_origin_tax_date(self, cr, uid, [invoice.id], context)                
                if not tax_date:
                    tax_date = invoice.date_invoice                
                
                sign = invoice.type == 'out_invoice' and 1 or -1
                lines1 = self.create_lines(cr, uid, invoice.invoice_line, sign)
                lines2 = self.create_shipping_lines(cr, uid, invoice.shipping_lines, sign)
                
                lines1.extend(lines2)
                if lines1:
                    account_tax_obj._get_compute_tax(cr, uid, avatax_config, invoice.date_invoice,
                                                   invoice.internal_number, not invoice.invoice_doc_no and 'SalesInvoice' or 'ReturnInvoice',
                                                   invoice.partner_id, shipping_add_origin_id,
                                                   shipping_add_id, lines1, invoice.user_id, invoice.exemption_code or None, invoice.exemption_code_id.code or None, 
                                                   True, tax_date,
                                                   invoice.invoice_doc_no, invoice.location_code or '', context=context)
            
        self.write(cr, uid, ids, {'state':'paid'}, context=context)
        return True
    
    
    def compute_tax(self, cr, uid, ids, context=None):
        """ """
        avatax_config_obj = self.pool.get('avalara.salestax')
        partner_obj = self.pool.get('res.partner')
        invoice_obj = self.pool.get('account.invoice.line')
        ship_order_line = self.pool.get('shipping.order.line')
        customer_date_validation = False
        
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
        if not avatax_config:
            raise osv.except_osv(_('AvaTax: Notice'), _('Please ensure AvaTax module is properly configured. \n\n Accounting->Configuration->AvaTax->AvaTax API'))
        for invoice in self.browse(cr, uid, ids, context=context):
#            c_code = partner_obj.browse(cr, uid, invoice.partner_id.id).country_id.code or False
#            cs_code = []        #Countries where Avalara address validation is enabled
            
            # Check partner address is valid
#            customer_date_validation = partner_obj.browse(cr, uid, invoice.partner_id.id).date_validation
#            if not customer_date_validation and not avatax_config.disable_tax_calculation:
#                raise osv.except_osv(_('Address Validation Error'), _('Customer does not have validated address or address is missing.  Make sure to Validate the customer\'s address in the AvaTax tab on the customer\'s settings.'))
                            
#            for c_brw in avatax_config.country_ids:
#                cs_code.append(str(c_brw.code))
            if avatax_config and not avatax_config.disable_tax_calculation :
#            and c_code in cs_code:
                pass
            else:
                for o_line in invoice.invoice_line:
                    invoice_obj.write(cr, uid, [o_line.id], {'tax_amt': 0.0,})
                for s_line in invoice.shipping_lines:
                    ship_order_line.write(cr, uid, [s_line.id], {'tax_amt': 0.0,})
        
        return True
    
    
    def button_dummy(self, cr, uid, ids, context=None):
        for inv in self.browse(cr, uid, ids, context=context):
            if not inv.invoice_line:
                raise osv.except_osv(_('No Invoice Lines !'), _('Please create some invoice lines.'))
#        self.compute_tax(cr, uid, ids, context=context)
        self.button_reset_taxes(cr, uid, ids, context=None)
        return True
    
    def action_commit_tax(self, cr, uid, ids, context=None):
        avatax_config_obj = self.pool.get('avalara.salestax')
        account_tax_obj = self.pool.get('account.tax')
#        partner_obj = self.pool.get('res.partner')
        invoice_obj = self.pool.get('account.invoice.line')
        ship_order_line = self.pool.get('shipping.order.line')
                
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)


        if avatax_config and avatax_config.disable_tax_reporting:
            return True
                
        for invoice in self.browse(cr, uid, ids, context=context):
            o_tax_amt = s_tax_amt = 0.0

            if avatax_config and not avatax_config.disable_tax_calculation and invoice.type in ['out_invoice','out_refund']:
                shipping_add_id = get_address_for_tax(self, cr, uid, [invoice.id], context)
                shipping_add_origin_id = get_origin_address_for_tax(self, cr, uid, [invoice.id], context)
                tax_date = get_origin_tax_date(self, cr, uid, [invoice.id], context)
                if not tax_date:
                    tax_date = invoice.date_invoice

                sign = invoice.type == 'out_invoice' and 1 or -1
                lines1 = self.create_lines(cr, uid, invoice.invoice_line, sign)
                lines2 = self.create_shipping_lines(cr, uid, invoice.shipping_lines, sign)
                
                if avatax_config.on_line:
                    for line1 in lines1:
                        ol_tax_amt =  account_tax_obj._get_compute_tax(cr, uid, avatax_config, invoice.date_invoice,
                                                                   invoice.internal_number, 'SalesOrder',
                                                                   invoice.partner_id, shipping_add_origin_id,
                                                                   shipping_add_id, [line1], invoice.user_id, invoice.exemption_code or None, invoice.exemption_code_id.code or None,
                                                                   context=context).TotalTax
                        o_tax_amt += ol_tax_amt  #tax amount based on total order line total   
                        invoice_obj.write(cr, uid, [line1['id']], {'tax_amt': ol_tax_amt})
                
                    #tax based on individual shipping order line
                    for line2, s_line in zip(lines2, invoice.shipping_lines):
                        sl_tax_amt = account_tax_obj._get_compute_tax(cr, uid, avatax_config, invoice.date_invoice,
                                                                   invoice.internal_number, 'SalesOrder',
                                                                   invoice.partner_id, shipping_add_origin_id,
                                                                   shipping_add_id, [line2], invoice.user_id, invoice.exemption_code or None, invoice.exemption_code_id.code or None,
                                                                   context=context).TotalTax
                        s_tax_amt += sl_tax_amt #tax amount based on total shipping line total
                        ship_order_line.write(cr, uid, [s_line.id], {'tax_amt': sl_tax_amt})
                        
                elif avatax_config.on_order:
                    for o_line in invoice.invoice_line:
                        invoice_obj.write(cr, uid, [o_line.id], {'tax_amt': 0.0,})
                    for s_line in invoice.shipping_lines:
                        ship_order_line.write(cr, uid, [s_line.id], {'tax_amt': 0.0,})
                else:
                    raise osv.except_osv(_('AvaTax: Warning !'), _('Please select system calls in API Configuration'))
                    
                       
                
                #extend list lines1 with lines2 to send all invoice lines in avalara    
                lines1.extend(lines2)
                if lines1:
                    account_tax_obj._get_compute_tax(cr, uid, avatax_config, invoice.date_invoice,
                                                   invoice.internal_number, not invoice.invoice_doc_no and 'SalesInvoice' or 'ReturnInvoice',
                                                   invoice.partner_id, shipping_add_origin_id,
                                                   shipping_add_id, lines1, invoice.user_id, invoice.exemption_code or None, invoice.exemption_code_id.code or None,
                                                   False, tax_date,
                                                   invoice.invoice_doc_no, invoice.location_code or '', context=context)
            else:
                for o_line in invoice.invoice_line:
                    invoice_obj.write(cr, uid, [o_line.id], {'tax_amt': 0.0,})
                for s_line in invoice.shipping_lines:
                    ship_order_line.write(cr, uid, [s_line.id], {'tax_amt': 0.0,})
        return True
    
    def create_shipping_lines(self, cr, uid, shipping_lines, sign):
        lines = []
        for line in shipping_lines:
            lines.append({
                'qty': 1,
                'itemcode': 'Ship/Freight',
                'description': 'Ship/Freight',
                'amount': sign * line.shipping_cost,
                'tax_code': line.ship_code_id.name,
            })
        return lines

    def create_lines(self, cr, uid, invoice_lines, sign):
        
        avatax_config_obj = self.pool.get('avalara.salestax')       
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
        lines = []
        for line in invoice_lines:
            
            # Add UPC to product item code           
            if line.product_id.ean13 and avatax_config.upc_enable:
                item_code =  "upc:" + line.product_id.ean13
            else:
                item_code = line.product_id.default_code
                
            # Get Tax Code 
            if line.product_id and line.product_id.tax_apply:
                tax_code = (line.product_id.tax_code_id and line.product_id.tax_code_id.name) or None
#            else:
#                tax_code = (line.product_id.categ_id.tax_code_id  and line.product_id.categ_id.tax_code_id.name) or None
           
            # Calculate discount amount
                discount_amount = 0.0
                is_discounted = False
                if line.discount != 0.0 or line.discount != None: 
                    discount_amount = sign * line.price_unit * ((line.discount or 0.0)/100.0) * line.quantity,
                    is_discounted = True
                lines.append({
                    'qty': line.quantity,
                    'itemcode': line.product_id and item_code or None,
                    'description': line.name,
                    'discounted': is_discounted,
                    'discount': discount_amount[0],
                    'amount': sign * line.price_unit * (1-(line.discount or 0.0)/100.0) * line.quantity,
                    'tax_code': tax_code,
                    'id': line.id,
                    'invoice_line_tax_id': line.invoice_line_tax_id,
                })
        return lines
    
    def _prepare_refund(self, cr, uid, invoice, date=None, period_id=None, description=None, journal_id=None, context=None):
        return super(account_invoice, self)._prepare_refund(cr, uid, invoice, date=date, period_id=period_id, description=description, journal_id=journal_id, context=context)
    

    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None, context=None):
        refund_ids = []
        shipping_ids = []
        partner_obj = self.pool.get('res.partner')
        
        for invoice in self.browse(cr, uid, ids, context=context):
            invoice_data = self._prepare_refund(cr, uid, invoice,
                                                date=date,
                                                period_id=period_id,
                                                description=description,
                                                journal_id=journal_id,
                                                context=context)
            
            for ship_line in invoice.shipping_lines:
                ship_brw = self.pool.get('shipping.order.line').browse(cr, uid, ship_line.id)
                vals = {
                    'name': ship_brw.name,
                    'ship_method_id': ship_brw.ship_method_id.id or None,
                    'shipping_cost':ship_brw.shipping_cost,
                    'ship_code_id': ship_brw.ship_code_id.id or None,
                    'sale_account_id': ship_brw.sale_account_id.id or None,
                    'tax_amt': ship_brw.tax_amt,
                    'sale_ship_id': ship_brw.sale_ship_id.id or None,
                    'invoice_ship_id': ship_brw.invoice_ship_id.id or None,
                    }
                shipping_ids.append((0,0,vals))
            
            
            invoice_data.update({
                            'shipping_lines':shipping_ids,
                        })
            # create the new invoice
            refund_ids.append(self.create(cr, uid, invoice_data, context=context))
            res_obj = partner_obj.browse(cr, uid, invoice.partner_id.id)
            self.write(cr, uid, refund_ids[0], {
                'invoice_doc_no': invoice.internal_number,
                'invoice_date': invoice.date_invoice,
                'tax_add_default': invoice.tax_add_default,
                'tax_add_invoice': invoice.tax_add_invoice,
                'tax_add_shipping': invoice.tax_add_shipping,
                'warehouse_id': invoice.warehouse_id.id,     
                'location_code': invoice.location_code,                                          
                })    
        return refund_ids

    def action_cancel(self, cr, uid, ids, *args):
        account_tax_obj = self.pool.get('account.tax')
        avatax_config_obj = self.pool.get('avalara.salestax')
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
        partner_obj = self.pool.get('res.partner')
        res = super(account_invoice, self).action_cancel(cr, uid, ids, *args)

        for invoice in self.browse(cr, uid, ids, *args):
            c_code = partner_obj.browse(cr, uid, invoice.partner_id.id).country_id.code or False
            cs_code = []        #Countries where Avalara address validation is enabled
            for c_brw in avatax_config.country_ids:
                cs_code.append(str(c_brw.code))
            if avatax_config and not avatax_config.disable_tax_calculation and invoice.type in ['out_invoice','out_refund'] and c_code in cs_code:
                doc_type = invoice.type == 'out_invoice' and 'SalesInvoice' or 'ReturnInvoice'
                account_tax_obj.cancel_tax(cr, uid, avatax_config, invoice.internal_number, doc_type, 'DocVoided')
        self.write(cr, uid, ids, {'internal_number':''})
        return res

    def check_tax_lines(self, compute_taxes):
        # Adapt new environment
        inv = self
        recs = self.env['account.invoice.tax']
        uid = recs.env.uid
        cr = recs.env.cr
        
        
        ait_obj = self.pool.get('account.invoice.tax')
        avatax_config_obj = self.pool.get('avalara.salestax')
        avatax_config = avatax_config_obj._get_avatax_config_company(cr,uid)
        partner_obj = self.pool.get('res.partner')
        c_code = partner_obj.browse(cr, uid, inv.partner_id.id).country_id.code or False
        
        cs_code = []        #Countries where Avalara address validation is enabled
        for c_brw in avatax_config.country_ids:
            cs_code.append(str(c_brw.code))
        #invoice type check when avalara config working and supplier invoice refund by default functionality
        if avatax_config and not avatax_config.disable_tax_calculation and inv.type in ['out_invoice', 'out_refund'] and c_code in cs_code:
            if not inv.tax_line:
                for tax in compute_taxes.values():
                    ait_obj.create(cr, uid, tax)
            else:
                tax_key = []
                for tax in inv.tax_line:
                    if tax.manual:
                        continue
                    key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id)
                    
                    tax_key.append(key)
                    if not key in compute_taxes:
                        raise osv.except_osv(_('Warning!'), _('Global taxes defined, but they are not in invoice lines !'))
                    base = compute_taxes[key]['base']
                    if abs(base - tax.base) > inv.company_id.currency_id.rounding:
                        raise osv.except_osv(_('Warning!'), _('Tax base different!\nClick on compute to update the tax base.'))
                for key in compute_taxes:
                    if not key in tax_key:
                        raise osv.except_osv(_('Warning!'), _('Taxes are missing!\nClick on compute button.'))
            
                for tax in inv.tax_line:
                    key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id)
                    if abs(compute_taxes[key]['amount'] - tax.amount) > inv.company_id.currency_id.rounding:
                        raise osv.except_osv(_('Warning !'), _('Tax amount different !\nClick on compute to update tax base'))
        else:
            #super(account_invoice, self).check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)
            super(account_invoice, self).check_tax_lines(compute_taxes)
        return True    
            
account_invoice()

class account_invoice_tax(osv.osv):
    _inherit = "account.invoice.tax"
    
    def create_lines(self, cr, uid, order_lines):
       lines = []
       for line in order_lines:
            if line.product_id and line.product_id.tax_apply:
                tax_code =  (line.product_id.tax_code_id and line.product_id.tax_code_id.name) or None
#            else:
#                tax_code = (line.product_id.categ_id.tax_code_id  and line.product_id.categ_id.tax_code_id.name) or None
           
                lines.append({
                   'qty': line.quantity,
                   'itemcode': line.product_id and line.product_id.default_code or None,
                   'description': line.name,
                   'amount': line.price_unit * (1-(line.discount or 0.0)/100.0) * line.quantity,
                   'tax_code': tax_code,
                   'id': line.id,
                   'invoice_line_tax_id': line.invoice_line_tax_id,
                })
       return lines
   
    def create_shipping_lines(self, cr, uid, shipping_lines):
         lines = []
         for line in shipping_lines:
             lines.append({
                 'qty': 1,
                 'itemcode': 'Ship/Freight',
                 'description': 'Ship/Freight',
                 'amount': line.shipping_cost,
                 'tax_code': line.ship_code_id.name,
             })
         return lines

    def compute(self, cr, uid, invoice_id, context=None):
        """compute tax after validate partner address, company credential and tax id and state"""
        tax_grouped = {}
        avatax_config_obj = self.pool.get('avalara.salestax')
        invoice_obj = self.pool.get('account.invoice')
        account_tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        invoice_line_obj = self.pool.get('account.invoice.line')
        ship_order_line = self.pool.get('shipping.order.line')
        is_avatax = False
        #invoice_id = invoice_id.id
        # update invoice id to check if obj or just id is passed in, adapat to different function calls from new Odoo acct funct
        if not isinstance(invoice_id, int): #invoice_id.id:
            invoice_id = invoice_id.id
            
        invoice = invoice_obj.browse(cr, uid, invoice_id, context=context)
        cur = invoice.currency_id
        company_currency = invoice.company_id.currency_id.id
        
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
        
        lines1 = []
        lines2 = []
        o_tax_amt = 0.0
        s_tax_amt = 0.0
        tax_id = []
        tax_amount = 0.0
        
#        c_code = partner_obj.browse(cr, uid, invoice.partner_id.id).country_id.code or False
#        cs_code = []        #Countries where Avalara address validation is enabled
#        for c_brw in avatax_config.country_ids:
#            cs_code.append(str(c_brw.code))
        if avatax_config and not avatax_config.disable_tax_calculation and invoice.type in ['out_invoice','out_refund']: 
#        and c_code in cs_code:
            
            # ship from Address / Origin Address either warehouse or company if none
            ava_tax  = account_tax_obj.search(cr, uid,
                                [('is_avatax','=',True),
                                ('type_tax_use','in', ['sale','all']),
                                ('company_id', '=', invoice.company_id.id)])
            if not invoice.warehouse_id.partner_id.id:
                ship_from_address_id = invoice.company_id.partner_id.id
            else:
                ship_from_address_id = invoice.warehouse_id.partner_id.id
            
            shipping_add_id = get_address_for_tax(self, cr, uid, [invoice_id], context)
            if invoice.invoice_line:
                lines1 = self.create_lines(cr, uid, invoice.invoice_line)
                lines2 = self.create_shipping_lines(cr, uid, invoice.shipping_lines)
                cal_lines = len(lines1)
                if avatax_config.on_line:
                    for line1 in lines1:
                        tax_id = 'invoice_line_tax_id' in line1 and [tax.id for tax in line1['invoice_line_tax_id']] or []
                        if tax_id and ava_tax and ava_tax[0] not in tax_id:
                            tax_id.append(ava_tax[0])
                        ol_tax_amt =  account_tax_obj._get_compute_tax(cr, uid, avatax_config, invoice.date_invoice or time.strftime('%Y-%m-%d'),
                                                                   invoice.internal_number, 'SalesOrder',
                                                                   invoice.partner_id, ship_from_address_id,
                                                                   shipping_add_id, [line1], invoice.user_id, invoice.exemption_code or None, invoice.exemption_code_id.code or None,
                                                                   context=context).TotalTax
                        o_tax_amt += ol_tax_amt
                        invoice_line_obj.write(cr, uid, [line1['id']], {'tax_amt': ol_tax_amt, 'invoice_line_tax_id': [(6,0, tax_id)]})
                
                    #tax based on individual shipping order line
                    if invoice.shipping_lines:
                        for line2, s_line in zip(lines2, invoice.shipping_lines):
                            sl_tax_amt = account_tax_obj._get_compute_tax(cr, uid, avatax_config, invoice.date_invoice or time.strftime('%Y-%m-%d'),
                                                                       invoice.internal_number, 'SalesOrder',
                                                                       invoice.partner_id, ship_from_address_id,
                                                                       shipping_add_id, [line2], invoice.user_id, invoice.exemption_code or None, invoice.exemption_code_id.code or None,
                                                                       context=context).TotalTax
                            s_tax_amt += sl_tax_amt #tax amount based on total shipping line total
                            ship_order_line.write(cr, uid, [s_line.id], {'tax_amt': sl_tax_amt,})
                
                elif avatax_config.on_order:
                    for o_line in invoice.invoice_line:
                        invoice_line_obj.write(cr, uid, [o_line.id], {'tax_amt': 0.0,})
                    for s_line in invoice.shipping_lines:
                        ship_order_line.write(cr, uid, [s_line.id], {'tax_amt': 0.0,})
                else:
                    raise osv.except_osv(_('AvaTax: Warning !'), _('Please select system calls in API Configuration'))    
                
                lines1.extend(lines2)
                if lines1:
                    tax_amount = account_tax_obj._get_compute_tax(cr, uid, avatax_config, invoice.date_invoice or time.strftime('%Y-%m-%d'),
                                                            invoice.internal_number, 'SalesOrder', invoice.partner_id, ship_from_address_id,
                                                            shipping_add_id, lines1, invoice.user_id, invoice.exemption_code or None, invoice.exemption_code_id.code or None,
                                                            context=context).TotalTax
                
                
                for line in invoice.invoice_line:
                    if line.product_id and line.product_id.tax_apply:
                        if ava_tax:
                            tax_brw = account_tax_obj.browse(cr, uid, ava_tax[0])
                            taxes = account_tax_obj.browse(cr, uid, ava_tax)
                            if not tax_brw.account_collected_id or not tax_brw.account_paid_id or not tax_brw.base_code_id or not tax_brw.tax_code_id or not tax_brw.ref_base_code_id or not tax_brw.ref_tax_code_id:
                                raise osv.except_osv(_('AvaTax: Warning !'), _('Please configure tax code information in "AVATAX" settings.  The documentation will assist you in proper configuration of all the tax code settings as well as how they relate to the product. \n\n Accounting->Configuration->Taxes->Taxes'))
                            for tax in account_tax_obj.compute_all(cr, uid, taxes, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, line.product_id, invoice.partner_id)['taxes']:
                                val={}
                                val['invoice_id'] = invoice.id
                                val['name'] = tax['name']
                                val['amount'] = tax_amount/cal_lines
                                val['manual'] = False
                                val['sequence'] = tax['sequence']
                                val['base'] = cur_obj.round(cr, uid, cur, tax['price_unit'] * line['quantity'])
                                if invoice.type in ('out_invoice','in_invoice'):
                                    val['base_code_id'] = tax['base_code_id']
                                    val['tax_code_id'] = tax['tax_code_id']
                                    val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                                    val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                                    val['base_sign'] = tax['base_sign']
                                else:
                                    val['base_code_id'] = tax['ref_base_code_id']
                                    val['ref_base_code_id'] = tax['ref_base_code_id']
                                    val['tax_code_id'] = tax['ref_tax_code_id']
                                    val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                                    val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                                    val['account_analytic_id'] = tax['account_analytic_paid_id']
                                    val['ref_base_sign'] = tax['ref_base_sign']

                                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                                if not key in tax_grouped:
                                    tax_grouped[key] = val
                                else:
                                    tax_grouped[key]['amount'] += val['amount']
                                    tax_grouped[key]['base'] += val['base']
                                    tax_grouped[key]['base_amount'] += val['base_amount']
                                    tax_grouped[key]['tax_amount'] += val['tax_amount']
                    
                    for tax in account_tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, line.product_id, invoice.partner_id)['taxes']:
                        if tax['id']:
                            is_avatax = account_tax_obj.browse(cr, uid, tax['id']).is_avatax
                        if is_avatax:
                            continue
                        else:
                            val={}
                            val['invoice_id'] = invoice.id
                            val['name'] = tax['name']
                            val['amount'] = tax['amount']
                            val['manual'] = False
                            val['sequence'] = tax['sequence']
                            val['base'] = cur_obj.round(cr, uid, cur, tax['price_unit'] * line['quantity'])

                            if invoice.type in ('out_invoice','in_invoice'):
                                val['base_code_id'] = tax['base_code_id']
                                val['tax_code_id'] = tax['tax_code_id']
                                val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                                val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                                val['account_id'] = tax['account_collected_id'] or line.account_id.id
                                val['account_analytic_id'] = tax['account_analytic_collected_id']
                                val['base_sign'] = tax['base_sign']
                            else:
                                val['base_code_id'] = tax['ref_base_code_id']
                                val['ref_base_code_id'] = tax['ref_base_code_id']
                                val['tax_code_id'] = tax['ref_tax_code_id']
                                val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                                val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                                val['account_id'] = tax['account_paid_id'] or line.account_id.id
                                val['account_analytic_id'] = tax['account_analytic_paid_id']
                                val['ref_base_sign'] = tax['ref_base_sign']

                            key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                            if not key in tax_grouped:
                                tax_grouped[key] = val
                            else:
                                tax_grouped[key]['amount'] += val['amount']
                                tax_grouped[key]['base'] += val['base']
                                tax_grouped[key]['base_amount'] += val['base_amount']
                                tax_grouped[key]['tax_amount'] += val['tax_amount']
                            
                for t in tax_grouped.values():
                    t['base'] = cur_obj.round(cr, uid, cur, t['base'])
                    t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
                    t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
                    t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
                return tax_grouped
        else:
            for line in invoice.invoice_line:
                for tax in account_tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, line.product_id, invoice.partner_id)['taxes']:
                    val={}
                    val['invoice_id'] = invoice.id
                    val['name'] = tax['name']
                    val['amount'] = tax['amount']
                    val['manual'] = False
                    val['sequence'] = tax['sequence']
                    val['base'] = cur_obj.round(cr, uid, cur, tax['price_unit'] * line['quantity'])
    
                    if invoice.type in ('out_invoice','in_invoice'):
                        val['base_code_id'] = tax['base_code_id']
                        val['tax_code_id'] = tax['tax_code_id']
                        val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                        val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                        val['account_id'] = tax['account_collected_id'] or line.account_id.id
                        val['account_analytic_id'] = tax['account_analytic_collected_id']
                        val['base_sign'] = tax['base_sign']
                    else:
                        val['base_code_id'] = tax['ref_base_code_id']
                        val['ref_base_code_id'] = tax['ref_base_code_id']
                        val['tax_code_id'] = tax['ref_tax_code_id']
                        val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                        val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                        val['account_id'] = tax['account_paid_id'] or line.account_id.id
                        val['account_analytic_id'] = tax['account_analytic_paid_id']
                        val['ref_base_sign'] = tax['ref_base_sign']
    
                    key = (val['tax_code_id'], val['base_code_id'], val['account_id'])   # removed optional Analytic ID  , val['account_analytic_id']
                    if not key in tax_grouped:
                        tax_grouped[key] = val
                    else:
                        tax_grouped[key]['amount'] += val['amount']
                        tax_grouped[key]['base'] += val['base']
                        tax_grouped[key]['base_amount'] += val['base_amount']
                        tax_grouped[key]['tax_amount'] += val['tax_amount']
                
    
            for t in tax_grouped.values():
                t['base'] = cur_obj.round(cr, uid, cur, t['base'])
                t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
                t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
                t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
            return tax_grouped                                                            

account_invoice_tax()



class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"

    def _weight_net(self, cr, uid, ids, field_name, arg, context):
        """Compute the net weight of the given Invoice Lines."""
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = 0.0

            if line.product_id:
                result[line.id] += (line.product_id.weight_net
                     * line.quantity)# / line.product_uom.factor)
        return result
    
    _columns = {
        'tax_amt': fields.float('Avalara Tax', help="tax calculate by avalara"),
        'weight_net': fields.function(_weight_net, method=True,
            readonly=True, string='Net Weight', help="The net weight in Kg.",
            store={
                # Low priority to compute this before fields in other modules
               'account.invoice.line': (lambda self, cr, uid, ids, c={}: ids,
                   ['quantity', 'product_id'], -11),
            },
        ),

    }
    
    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = []
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        invoice_obj = self.pool.get('account.invoice')
        ait_obj = self.pool.get('account.invoice.tax')
        avatax_config_obj = self.pool.get('avalara.salestax')
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
        
        invoice = invoice_obj.browse(cr, uid, invoice_id, context=context)
        company_currency = invoice.company_id.currency_id.id

        partner_obj = self.pool.get('res.partner')
        c_code = partner_obj.browse(cr, uid, invoice.partner_id.id).country_id.code or False
        cs_code = []        #Countries where Avalara address validation is enabled

        # Make sure Avatax is configured
        if not avatax_config:
            raise osv.except_osv(_('AvaTax: Error'), _('Your Avatax Countries settings are not configured. You need a country code in the Countries section.  \nIf you have a multi-company installation, you must add settings for each company.  \n\nYou can update settings in Avatax->Avatax API.'))
        
        for c_brw in avatax_config.country_ids:
            cs_code.append(str(c_brw.code))
        if avatax_config and not avatax_config.disable_tax_calculation and c_code in cs_code:
            for line in invoice.invoice_line:
                mres = self.move_line_get_item(cr, uid, line, context)
                if not mres:
                    continue
                res.append(mres)
                tax_code_found= False

                for tax in ait_obj.compute(cr, uid, invoice_id, context=context).values():
                    if invoice.type in ('out_invoice', 'in_invoice'):
                        tax_code_id = tax['base_code_id']
                        tax_amount = line.price_subtotal * tax['base_sign'] or 1.0
                    else:
                        tax_code_id = tax['ref_base_code_id']
                        tax_amount = line.price_subtotal * tax['ref_base_sign']
                    if tax_code_found:
                        if not tax_code_id:
                            continue
                        res.append(self.move_line_get_item(cr, uid, line, context))
                        res[-1]['price'] = 0.0
                        res[-1]['account_analytic_id'] = False
                    elif not tax_code_id:
                        continue
                    tax_code_found = True

                    res[-1]['tax_code_id'] = tax_code_id
                    res[-1]['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency,
                                                            tax_amount, context={'date': invoice.date_invoice})

        else:
            res = super(account_invoice_line, self).move_line_get( cr, uid, invoice_id, context=context)
        return res

account_invoice_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: