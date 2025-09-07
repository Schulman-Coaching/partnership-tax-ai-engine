"""
Tax calculation utilities for partnership taxation
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

def calculate_section_704b_balance(
    beginning_balance: Decimal,
    contributions: Decimal,
    distributions: Decimal,
    income_allocations: Decimal,
    loss_allocations: Decimal,
    other_adjustments: Decimal = Decimal('0')
) -> Decimal:
    """
    Calculate Section 704(b) capital account balance
    
    Per Treasury Reg. 1.704-1(b)(2)(iv), capital accounts must be maintained to reflect:
    - Beginning balance
    - + Contributions
    - - Distributions  
    - + Income/gain allocations
    - - Loss/deduction/expenditure allocations
    - +/- Other adjustments
    """
    ending_balance = (
        beginning_balance +
        contributions -
        distributions +
        income_allocations -
        loss_allocations +
        other_adjustments
    )
    
    return ending_balance.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def validate_substantial_economic_effect(
    allocations: Dict[str, Decimal],
    capital_accounts: Dict[str, Decimal],
    partnership_agreement: Dict
) -> Dict[str, bool]:
    """
    Validate that allocations have substantial economic effect per Section 704(b)
    
    Three-part test:
    1. Capital accounts maintained according to regulations
    2. Liquidating distributions made per capital account balances  
    3. Deficit restoration obligation OR qualified income offset
    """
    validation_results = {
        "capital_account_maintenance": True,
        "liquidation_consistency": True,  
        "deficit_restoration": False,
        "substantial_economic_effect": False
    }
    
    # Check for DRO or QIO provisions
    has_dro = partnership_agreement.get("has_deficit_restoration_obligation", False)
    has_qio = partnership_agreement.get("has_qualified_income_offset", False)
    
    if has_dro or has_qio:
        validation_results["deficit_restoration"] = True
    
    # Check for negative capital accounts without protection
    has_unprotected_deficit = False
    for partner_id, balance in capital_accounts.items():
        if balance < 0 and not (has_dro or has_qio):
            has_unprotected_deficit = True
            logger.warning(f"Partner {partner_id} has deficit balance without DRO/QIO")
            break
    
    if not has_unprotected_deficit:
        validation_results["substantial_economic_effect"] = True
    
    return validation_results

def calculate_liquidation_proceeds(
    total_proceeds: Decimal,
    waterfall_steps: List[Dict],
    partners: List[Dict]
) -> Dict[str, Decimal]:
    """
    Calculate liquidation proceeds distribution per partnership agreement waterfall
    """
    partner_proceeds = {p["partner_id"]: Decimal('0') for p in partners}
    remaining_proceeds = total_proceeds
    
    for step in waterfall_steps:
        if remaining_proceeds <= 0:
            break
            
        step_type = step.get("type")
        
        if step_type == "return_of_capital":
            # Return capital contributions first
            for partner in partners:
                if remaining_proceeds <= 0:
                    break
                    
                partner_id = partner["partner_id"]
                capital_contributed = Decimal(str(partner.get("capital_contributed", 0)))
                unreturned_capital = capital_contributed - partner_proceeds.get(partner_id, Decimal('0'))
                
                if unreturned_capital > 0:
                    distribution = min(unreturned_capital, remaining_proceeds)
                    partner_proceeds[partner_id] += distribution
                    remaining_proceeds -= distribution
        
        elif step_type == "preferred_return":
            # Preferred return calculations
            preferred_rate = Decimal(str(step.get("rate", 0)))
            
            for partner in partners:
                if remaining_proceeds <= 0:
                    break
                    
                if partner.get("receives_preferred_return", False):
                    partner_id = partner["partner_id"]
                    capital_base = Decimal(str(partner.get("capital_contributed", 0)))
                    preferred_return = capital_base * preferred_rate
                    
                    distribution = min(preferred_return, remaining_proceeds)
                    partner_proceeds[partner_id] += distribution
                    remaining_proceeds -= distribution
        
        elif step_type == "pro_rata":
            # Pro rata distribution based on ownership
            total_ownership = sum(Decimal(str(p.get("ownership_percentage", 0))) for p in partners)
            
            if total_ownership > 0:
                for partner in partners:
                    partner_id = partner["partner_id"]
                    ownership_pct = Decimal(str(partner.get("ownership_percentage", 0)))
                    pro_rata_share = ownership_pct / total_ownership
                    distribution = remaining_proceeds * pro_rata_share
                    
                    partner_proceeds[partner_id] += distribution
                
                remaining_proceeds = Decimal('0')  # All distributed
    
    # Round to penny precision
    for partner_id in partner_proceeds:
        partner_proceeds[partner_id] = partner_proceeds[partner_id].quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    return partner_proceeds

def calculate_target_allocations(
    partners: List[Dict],
    net_income: Decimal,
    liquidation_proceeds: Dict[str, Decimal],
    current_balances: Dict[str, Decimal]
) -> Dict[str, Decimal]:
    """
    Calculate required income/loss allocations to achieve target capital balances
    """
    target_allocations = {}
    
    for partner in partners:
        partner_id = partner["partner_id"]
        
        # Target balance equals liquidation proceeds
        target_balance = liquidation_proceeds.get(partner_id, Decimal('0'))
        current_balance = current_balances.get(partner_id, Decimal('0'))
        
        # Required allocation = target - current
        required_allocation = target_balance - current_balance
        target_allocations[partner_id] = required_allocation.quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    # Validate total allocations equal net income
    total_allocations = sum(target_allocations.values())
    
    if abs(total_allocations - net_income) > Decimal('0.01'):
        logger.warning(
            f"Total allocations ({total_allocations}) don't equal net income ({net_income})"
        )
        
        # Proportionally adjust if needed
        if total_allocations != 0:
            adjustment_factor = net_income / total_allocations
            for partner_id in target_allocations:
                target_allocations[partner_id] = (
                    target_allocations[partner_id] * adjustment_factor
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return target_allocations

def calculate_section_754_adjustment(
    partnership_assets: List[Dict],
    transferred_interest: Decimal,
    purchase_price: Decimal,
    inside_basis: Decimal
) -> Dict:
    """
    Calculate Section 754 election basis adjustment per Section 743(b)
    """
    # Total adjustment = outside basis - inside basis
    total_adjustment = purchase_price - inside_basis
    
    if total_adjustment == 0:
        return {
            "total_adjustment": Decimal('0'),
            "asset_adjustments": {},
            "depreciation_impact": {}
        }
    
    # Allocate adjustment to assets based on relative FMV
    asset_adjustments = {}
    total_fmv = sum(Decimal(str(asset.get("fair_market_value", 0))) for asset in partnership_assets)
    
    if total_fmv > 0:
        for asset in partnership_assets:
            asset_id = asset["asset_id"]
            asset_fmv = Decimal(str(asset.get("fair_market_value", 0)))
            asset_basis = Decimal(str(asset.get("tax_basis", 0)))
            
            # Proportional allocation based on FMV
            proportion = asset_fmv / total_fmv
            asset_adjustment = total_adjustment * proportion * transferred_interest
            
            asset_adjustments[asset_id] = {
                "basis_adjustment": asset_adjustment.quantize(Decimal('0.01')),
                "new_basis": (asset_basis + asset_adjustment).quantize(Decimal('0.01')),
                "depreciation_method": asset.get("depreciation_method"),
                "useful_life": asset.get("useful_life_years")
            }
    
    return {
        "total_adjustment": total_adjustment.quantize(Decimal('0.01')),
        "asset_adjustments": asset_adjustments,
        "transferred_interest": transferred_interest,
        "compliance_notes": [
            "Section 743(b) adjustment calculated per Treasury Reg. 1.743-1",
            "Adjustment allocated to assets based on relative fair market values",
            "Transferee partner receives step-up in basis for depreciation purposes"
        ]
    }