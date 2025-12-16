/** @odoo-module **/

import VariantMixin from "@website_sale/js/sale_variant_mixin";
import publicWidget from "@web/legacy/js/public/public_widget";
import "@website_sale_stock/js/variant_mixin";

function removeDuplicateStockInfo() {
    const stockInfos = document.querySelectorAll('#total_stock_info');
    if (stockInfos.length > 1) {
        for (let i = 1; i < stockInfos.length; i++) {
            stockInfos[i].remove();
        }
    }
}

const observer = new MutationObserver(() => {
    removeDuplicateStockInfo();
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});

setInterval(removeDuplicateStockInfo, 500);

const _onChangeCombinationStockOriginal = VariantMixin._onChangeCombinationStock;

VariantMixin._onChangeCombinationStock = function (ev, $parent, combination) {
    _onChangeCombinationStockOriginal.apply(this, arguments);
    
    let product_id = 0;
    if ($parent.find('input.product_id:checked').length) {
        product_id = $parent.find('input.product_id:checked').val();
    } else {
        product_id = $parent.find('.product_id').val();
    }
    const isMainProduct = combination.product_id &&
        ($parent.is('.js_main_product') || $parent.is('.main_product')) &&
        combination.product_id === parseInt(product_id);

    if (!this.isWebsite || !isMainProduct) {
        return;
    }

    let ctaWrapper = $parent[0].querySelector('#o_wsale_cta_wrapper');
    if (combination.is_out_of_stock && combination.product_type === 'product') {
        ctaWrapper.classList.replace('d-flex', 'd-none');
        ctaWrapper.classList.add('out_of_stock');
    }
};
