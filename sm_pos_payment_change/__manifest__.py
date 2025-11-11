 
{
    "name": "Point Of Sale - Change Payments",
    "version": "17.0.1.0.0",
    "summary": "Allow cashier to change order payments, as long as"
    " the session is not closed.",
    "category": "Point Of Sale",
    "author": "SAN MIGUEL, S.A.",
  
    
    "depends": ["point_of_sale"],
    
    "development_status": "Beta",
    "data": [
        "security/ir.model.access.csv",
        "wizards/view_pos_payment_change_wizard.xml",
        "views/view_pos_config.xml",
        "views/view_pos_order.xml",
    ],
    "installable": True,
}
