"""
Capital Account Manager Service
Implements Section 704(b) capital account maintenance and target allocation calculations
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
import uuid

from app.models.partnership import Partner, CapitalAccount, Transaction, AllocationResult
from app.utils.tax_calculations import (
    calculate_section_704b_balance,
    validate_substantial_economic_effect,
    calculate_liquidation_proceeds
)

logger = logging.getLogger(__name__)

@dataclass
class TargetAllocationResult:
    """Result of target allocation calculation"""
    target_balances: Dict[str, Decimal]
    required_allocations: Dict[str, Decimal]
    compliance_check: Dict[str, bool]
    calculation_method: str
    waterfall_analysis: Dict

@dataclass
class TransactionResult:
    """Result of processing a capital account transaction"""
    transaction_id: str
    updated_balances: Dict[str, Decimal]
    compliance_status: bool
    validation_messages: List[str]

class CapitalAccountManager:
    """
    Manages Section 704(b) capital accounts and target allocations
    
    This class implements the complex logic required for partnership tax compliance,
    including capital account maintenance according to Treasury Regulation 1.704-1(b),
    target allocation calculations, and substantial economic effect validation.
    """
    
    def __init__(self):
        self.precision = Decimal('0.01')  # Penny precision for tax calculations
        
    async def get_capital_accounts(self, partnership_id: str) -> Dict:
        """Get current capital accounts for all partners in a partnership"""
        try:
            # This would typically query the database
            # For MVP, returning placeholder data structure
            return {
                "partnership_id": partnership_id,
                "accounts": [],
                "account_method": "section_704b",
                "last_updated": datetime.utcnow().isoformat(),
                "compliance_status": "compliant"
            }
            
        except Exception as e:
            logger.error(f"Error retrieving capital accounts for {partnership_id}: {str(e)}")
            raise
    
    async def process_transaction(
        self, 
        partnership_id: str, 
        transaction_data: Dict
    ) -> TransactionResult:
        """
        Process a capital account transaction
        
        Args:
            partnership_id: Partnership identifier
            transaction_data: Transaction details including type, amount, partner, etc.
            
        Returns:
            TransactionResult with updated balances and compliance status
        """
        try:
            transaction_id = str(uuid.uuid4())
            
            # Validate transaction data
            validation_messages = self._validate_transaction_data(transaction_data)
            if validation_messages:
                raise ValueError(f"Invalid transaction data: {'; '.join(validation_messages)}")
            
            # Process the transaction based on type
            transaction_type = transaction_data.get("transaction_type")
            
            if transaction_type == "contribution":
                result = await self._process_contribution(partnership_id, transaction_data)
            elif transaction_type == "distribution":
                result = await self._process_distribution(partnership_id, transaction_data)
            elif transaction_type == "allocation":
                result = await self._process_allocation(partnership_id, transaction_data)
            elif transaction_type == "revaluation":
                result = await self._process_revaluation(partnership_id, transaction_data)
            else:
                raise ValueError(f"Unknown transaction type: {transaction_type}")
            
            # Check compliance after transaction
            compliance_status = await self._check_compliance(partnership_id)
            
            return TransactionResult(
                transaction_id=transaction_id,
                updated_balances=result,
                compliance_status=compliance_status,
                validation_messages=[]
            )
            
        except Exception as e:
            logger.error(f"Error processing transaction for {partnership_id}: {str(e)}")
            raise
    
    async def calculate_target_allocations(
        self, 
        partnership_id: str, 
        calculation_data: Dict
    ) -> TargetAllocationResult:
        """
        Calculate target allocations to achieve desired capital account balances
        
        This is the core functionality that automates the complex "target allocation"
        methodology used by sophisticated partnerships.
        
        Args:
            partnership_id: Partnership identifier
            calculation_data: Year-end financial data and partnership agreement terms
            
        Returns:
            TargetAllocationResult with required allocations and compliance analysis
        """
        try:
            logger.info(f"Calculating target allocations for partnership {partnership_id}")
            
            # Extract key data from calculation request
            partners = calculation_data.get("partners", [])
            net_income = Decimal(str(calculation_data.get("net_income", 0)))
            agreement_terms = calculation_data.get("agreement_terms", {})
            
            # Step 1: Model hypothetical liquidation
            liquidation_analysis = await self._model_liquidation_distribution(
                partners, 
                agreement_terms,
                calculation_data.get("asset_values", {})
            )
            
            # Step 2: Calculate target capital account balances
            target_balances = self._calculate_target_balances(
                partners, 
                liquidation_analysis
            )
            
            # Step 3: Determine required allocations to reach targets
            required_allocations = self._calculate_required_allocations(
                partners,
                target_balances,
                net_income
            )
            
            # Step 4: Validate substantial economic effect
            compliance_check = self._validate_allocations_compliance(
                required_allocations,
                agreement_terms,
                target_balances
            )
            
            result = TargetAllocationResult(
                target_balances=target_balances,
                required_allocations=required_allocations,
                compliance_check=compliance_check,
                calculation_method="target_capital_account",
                waterfall_analysis=liquidation_analysis
            )
            
            logger.info(f"Target allocation calculation completed for {partnership_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating target allocations for {partnership_id}: {str(e)}")
            raise
    
    def _validate_transaction_data(self, transaction_data: Dict) -> List[str]:
        """Validate transaction data for completeness and accuracy"""
        errors = []
        
        required_fields = ["transaction_type", "partner_id", "amount", "transaction_date"]
        for field in required_fields:
            if field not in transaction_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate amount is numeric
        try:
            amount = Decimal(str(transaction_data.get("amount", 0)))
            if amount < 0 and transaction_data.get("transaction_type") not in ["distribution"]:
                errors.append("Amount cannot be negative for this transaction type")
        except (ValueError, TypeError):
            errors.append("Amount must be a valid number")
        
        # Validate date format
        try:
            date_str = transaction_data.get("transaction_date")
            if date_str:
                datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            errors.append("Invalid date format")
        
        return errors
    
    async def _process_contribution(self, partnership_id: str, transaction_data: Dict) -> Dict[str, Decimal]:
        """Process a capital contribution transaction"""
        partner_id = transaction_data["partner_id"]
        amount = Decimal(str(transaction_data["amount"]))
        
        # In a full implementation, this would:
        # 1. Update the partner's capital account balance
        # 2. Record the transaction in the audit trail
        # 3. Update any related tax basis tracking
        
        logger.info(f"Processing contribution: ${amount} from partner {partner_id}")
        
        # Placeholder return - in real implementation, return updated balances
        return {
            partner_id: amount  # This would be the new balance, not just the contribution
        }
    
    async def _process_distribution(self, partnership_id: str, transaction_data: Dict) -> Dict[str, Decimal]:
        """Process a distribution transaction"""
        partner_id = transaction_data["partner_id"]
        amount = Decimal(str(transaction_data["amount"]))
        
        logger.info(f"Processing distribution: ${amount} to partner {partner_id}")
        
        # Placeholder implementation
        return {
            partner_id: -amount  # This would be the balance change
        }
    
    async def _process_allocation(self, partnership_id: str, transaction_data: Dict) -> Dict[str, Decimal]:
        """Process an income/loss allocation transaction"""
        partner_id = transaction_data["partner_id"]
        amount = Decimal(str(transaction_data["amount"]))
        allocation_type = transaction_data.get("allocation_type", "income")
        
        logger.info(f"Processing {allocation_type} allocation: ${amount} to partner {partner_id}")
        
        # Placeholder implementation
        return {
            partner_id: amount if allocation_type == "income" else -amount
        }
    
    async def _process_revaluation(self, partnership_id: str, transaction_data: Dict) -> Dict[str, Decimal]:
        """Process a Section 704(b) book revaluation"""
        revaluation_amount = Decimal(str(transaction_data.get("revaluation_amount", 0)))
        partners = transaction_data.get("partners", [])
        
        logger.info(f"Processing revaluation: ${revaluation_amount}")
        
        # Allocate revaluation based on partnership interests
        updated_balances = {}
        for partner in partners:
            partner_id = partner["partner_id"]
            ownership_pct = Decimal(str(partner.get("ownership_percentage", 0))) / 100
            partner_allocation = (revaluation_amount * ownership_pct).quantize(self.precision)
            updated_balances[partner_id] = partner_allocation
        
        return updated_balances
    
    async def _model_liquidation_distribution(
        self, 
        partners: List[Dict], 
        agreement_terms: Dict,
        asset_values: Dict
    ) -> Dict:
        """
        Model a hypothetical liquidation to determine distribution proceeds
        
        This implements the complex waterfall analysis required for target allocations
        """
        try:
            # Extract waterfall terms from agreement
            waterfall_steps = agreement_terms.get("distribution_waterfall", [])
            total_proceeds = Decimal(str(asset_values.get("total_fair_market_value", 0)))
            
            logger.info(f"Modeling liquidation with proceeds: ${total_proceeds}")
            
            # Initialize partner distribution tracking
            partner_distributions = {p["partner_id"]: Decimal('0') for p in partners}
            remaining_proceeds = total_proceeds
            
            # Process each waterfall step
            for step in waterfall_steps:
                step_type = step.get("type")
                step_amount = Decimal(str(step.get("amount", 0)))
                
                if step_type == "return_of_capital":
                    # Return of capital contributions first
                    for partner in partners:
                        partner_id = partner["partner_id"]
                        capital_contributed = Decimal(str(partner.get("capital_contributed", 0)))
                        distribution = min(capital_contributed, remaining_proceeds)
                        
                        partner_distributions[partner_id] += distribution
                        remaining_proceeds -= distribution
                        
                        if remaining_proceeds <= 0:
                            break
                
                elif step_type == "preferred_return":
                    # Preferred return to limited partners
                    preferred_rate = Decimal(str(step.get("rate", 0)))
                    for partner in partners:
                        if partner.get("partner_type") == "limited":
                            partner_id = partner["partner_id"]
                            capital_base = Decimal(str(partner.get("capital_contributed", 0)))
                            preferred_return = capital_base * preferred_rate
                            distribution = min(preferred_return, remaining_proceeds)
                            
                            partner_distributions[partner_id] += distribution
                            remaining_proceeds -= distribution
                
                elif step_type == "catch_up":
                    # Catch-up to general partner
                    catch_up_percentage = Decimal(str(step.get("percentage", 0))) / 100
                    for partner in partners:
                        if partner.get("partner_type") == "general":
                            partner_id = partner["partner_id"]
                            catch_up_amount = remaining_proceeds * catch_up_percentage
                            
                            partner_distributions[partner_id] += catch_up_amount
                            remaining_proceeds -= catch_up_amount
                
                elif step_type == "promote":
                    # Carried interest/promote distribution
                    promote_percentage = Decimal(str(step.get("percentage", 0))) / 100
                    for partner in partners:
                        if partner.get("receives_promote", False):
                            partner_id = partner["partner_id"]
                            promote_amount = remaining_proceeds * promote_percentage
                            
                            partner_distributions[partner_id] += promote_amount
                            remaining_proceeds -= promote_amount
                
                elif step_type == "pro_rata":
                    # Remaining proceeds distributed pro rata
                    total_interests = sum(Decimal(str(p.get("ownership_percentage", 0))) for p in partners)
                    
                    for partner in partners:
                        partner_id = partner["partner_id"]
                        ownership_pct = Decimal(str(partner.get("ownership_percentage", 0)))
                        pro_rata_share = (ownership_pct / total_interests) if total_interests > 0 else 0
                        distribution = remaining_proceeds * pro_rata_share
                        
                        partner_distributions[partner_id] += distribution
                
                # Break if no proceeds remaining
                if remaining_proceeds <= 0:
                    break
            
            return {
                "total_proceeds": total_proceeds,
                "partner_distributions": partner_distributions,
                "waterfall_steps_processed": len(waterfall_steps),
                "remaining_proceeds": remaining_proceeds
            }
            
        except Exception as e:
            logger.error(f"Error modeling liquidation: {str(e)}")
            raise
    
    def _calculate_target_balances(
        self, 
        partners: List[Dict], 
        liquidation_analysis: Dict
    ) -> Dict[str, Decimal]:
        """Calculate target capital account balances based on liquidation analysis"""
        
        partner_distributions = liquidation_analysis["partner_distributions"]
        target_balances = {}
        
        for partner in partners:
            partner_id = partner["partner_id"]
            
            # Target balance equals what partner would receive in liquidation
            target_balance = partner_distributions.get(partner_id, Decimal('0'))
            target_balances[partner_id] = target_balance.quantize(self.precision)
        
        logger.info(f"Calculated target balances for {len(partners)} partners")
        return target_balances
    
    def _calculate_required_allocations(
        self,
        partners: List[Dict],
        target_balances: Dict[str, Decimal],
        net_income: Decimal
    ) -> Dict[str, Decimal]:
        """Calculate income/loss allocations needed to reach target balances"""
        
        required_allocations = {}
        total_current_balances = Decimal('0')
        
        # Calculate current balances and required changes
        for partner in partners:
            partner_id = partner["partner_id"]
            current_balance = Decimal(str(partner.get("current_capital_balance", 0)))
            target_balance = target_balances.get(partner_id, Decimal('0'))
            
            required_allocation = target_balance - current_balance
            required_allocations[partner_id] = required_allocation.quantize(self.precision)
            total_current_balances += current_balance
        
        # Validate that total allocations equal net income
        total_allocations = sum(required_allocations.values())
        
        if abs(total_allocations - net_income) > self.precision:
            logger.warning(f"Allocation total ({total_allocations}) doesn't match net income ({net_income})")
            
            # Adjust allocations proportionally to match net income
            if total_allocations != 0:
                adjustment_factor = net_income / total_allocations
                for partner_id in required_allocations:
                    required_allocations[partner_id] = (
                        required_allocations[partner_id] * adjustment_factor
                    ).quantize(self.precision)
        
        return required_allocations
    
    def _validate_allocations_compliance(
        self,
        allocations: Dict[str, Decimal],
        agreement_terms: Dict,
        target_balances: Dict[str, Decimal]
    ) -> Dict[str, bool]:
        """Validate that proposed allocations meet Section 704(b) requirements"""
        
        compliance_check = {
            "substantial_economic_effect": True,
            "capital_account_maintenance": True,
            "liquidation_consistency": True,
            "deficit_restoration_obligation": True
        }
        
        # Check if agreement has required DRO or QIO provisions
        has_dro = agreement_terms.get("has_deficit_restoration_obligation", False)
        has_qio = agreement_terms.get("has_qualified_income_offset", False)
        
        if not (has_dro or has_qio):
            compliance_check["deficit_restoration_obligation"] = False
            logger.warning("Partnership agreement lacks DRO or QIO provisions")
        
        # Check that allocations follow economic arrangement
        # This would include more sophisticated validation in a full implementation
        
        # Check for negative capital account balances without protection
        for partner_id, balance in target_balances.items():
            if balance < 0 and not has_dro and not has_qio:
                compliance_check["substantial_economic_effect"] = False
                logger.warning(f"Partner {partner_id} would have deficit balance without DRO/QIO")
        
        return compliance_check
    
    async def _check_compliance(self, partnership_id: str) -> bool:
        """Check overall partnership compliance status"""
        # This would perform comprehensive compliance checks
        # For MVP, return True as placeholder
        return True