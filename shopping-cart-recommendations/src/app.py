import pandas as pd

from h2o_wave import Q, app, copy_expando, main, ui

from .config import config


def get_product_mapping() -> dict:
    """
    Mapping of product to department.
    """
    df = pd.read_csv('data/instacart_products.csv')
    product_names = df.product_name.values
    department_names = df.department.values
    product_mapping = {}

    for i in range(df.shape[0]):
        product_mapping[product_names[i]] = department_names[i]

    product_mapping['No recommendations available'] = 'Please change products in cart'

    return product_mapping


def get_profitability_bucket(profitability: float) -> str:
    """
    Profitability bucket.
    """
    if profitability >= 0.25:
        return "Very High"
    elif profitability >= 0.20:
        return "High"
    elif profitability >= 0.10:
        return "Medium"
    elif profitability >= 0.05:
        return "Low"
    else:
        return "Very Low"


def get_diversity_bucket(diversity: float) -> str:
    """
    Diversity bucket.
    """
    if diversity >= 0.99:
        return "Full"
    elif diversity >= 0.51:
        return "High"
    elif diversity >= 0.49:
        return "Balanced"
    elif diversity > 0.0:
        return "Low"
    else:
        return "None"


def get_diversity_color(diversity: float) -> str:
    """
    Color of diversity stat.
    """
    if diversity in [0.0, 1.0]:
        return 'green'
    else:
        return 'orange'


async def initialize_app(q: Q):
    q.client.rulesets = pd.read_csv('data/instacart_market_basket_model.csv').sort_values('profitability', ascending=False)
    q.client.rulesets.consequents = q.client.rulesets.consequents.apply(lambda x: list(eval(x))[0])
    q.client.product_department = get_product_mapping()
    q.client.product_choices = [ui.choice(name=str(x), label=str(x)) for x, _ in q.client.product_department.items()]
    q.client.df = q.client.rulesets.copy(deep=True)
    q.client.cart_products = ['Banana']
    q.client.suggested_products = ['Organic Hass Avocado', 'Large Lemon', 'Biscoff Cookie']

    q.page.add('header', ui.header_card(
        box=config.boxes['banner'],
        title=config.title,
        subtitle=config.subtitle,
        icon=config.icon,
        icon_color=config.icon_color,
    ))

    q.page.add('cart', ui.form_card(
        box=config.boxes['cart'],
        items=[
            ui.separator('Cart'),
            ui.text('Add products to the cart below and simulate the top recommendations.'),
            ui.picker(
                name='cart_products',
                choices=q.client.product_choices
            ),
            ui.button(name='simulate', label='Simulate', primary=True),
        ]
    ))

    q.page.add('suggestions', ui.form_card(
        box=config.boxes['suggestions'],
        items=[
            ui.separator(label='Suggestions'),
            ui.button(name='suggested_product_1', caption='Add to cart', primary=False),
            ui.button(name='suggested_product_2', caption='Add to cart', primary=False),
            ui.button(name='suggested_product_3', caption='Add to cart', primary=False)
        ]
    ))

    await update_cart(q, add_product=False)
    await q.page.save()


async def update_cart(q: Q, add_product: bool = True):
    """
    Update cart.
    """
    if add_product:
        if q.client.suggested_product_1:
            new_product = q.client.suggested_products[0]
        elif q.client.suggested_product_2:
            new_product = q.client.suggested_products[1]
        elif q.client.suggested_product_3:
            new_product = q.client.suggested_products[2]
        else:
            new_product = []

        q.client.cart_products += [new_product]

        q.client.suggested_products = q.client.df[
                                          q.client.df.antecedents.str.contains(f"'{new_product}'")
                                      ].consequents.values[:3]

    q.page['cart'].items[2].picker.values = q.client.cart_products

    q.page['suggestions'].items[1].button.visible = False
    q.page['suggestions'].items[2].button.visible = False
    q.page['suggestions'].items[3].button.visible = False

    if len(q.client.suggested_products) > 0:
        q.page['suggestions'].items[1].button.visible = True
        q.page['suggestions'].items[1].button.label = q.client.suggested_products[0]

    if len(q.client.suggested_products) > 1:
        q.page['suggestions'].items[2].button.visible = True
        q.page['suggestions'].items[2].button.label = q.client.suggested_products[1]

    if len(q.client.suggested_products) > 2:
        q.page['suggestions'].items[3].button.visible = True
        q.page['suggestions'].items[3].button.label = q.client.suggested_products[2]

    await q.page.save()


@app('/')
async def serve(q: Q):
    """
    Main serving function.
    """
    if not q.client.initialized:
        await initialize_app(q)
        q.client.initialized = True
    if q.args.suggested_product_1 or q.args.suggested_product_2 or q.args.suggested_product_3:
        copy_expando(q.args, q.client)
        await update_cart(q, add_product=True)
    elif q.args.simulate:
        copy_expando(q.args, q.client)
        if len(q.client.cart_products) == 0:
            q.client.cart_products = ['None']
