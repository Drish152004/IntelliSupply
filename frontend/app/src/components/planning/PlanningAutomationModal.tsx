import { Settings2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import PlanningAutomationPanel from '@/components/planning/PlanningAutomationPanel';
import PlanningAuditLogPanel from '@/components/planning/PlanningAuditLogPanel';
import type { ActionAuditLog, AutomationPolicy } from '@/lib/planningTypes';

interface PlanningAutomationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  policies: AutomationPolicy[];
  policiesLoading: boolean;
  auditLogs: ActionAuditLog[];
  auditLoading: boolean;
  onPolicyChange: (policyType: string, patch: Partial<AutomationPolicy>) => void;
  onSavePolicy: (policyType: string) => void;
  savingPolicyType: string | null;
}

export default function PlanningAutomationModal({
  open,
  onOpenChange,
  policies,
  policiesLoading,
  auditLogs,
  auditLoading,
  onPolicyChange,
  onSavePolicy,
  savingPolicyType,
}: PlanningAutomationModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[900px] max-h-[85vh] overflow-hidden flex flex-col rounded-[1.5rem]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-indigo-600" />
            Automation Settings
          </DialogTitle>
          <DialogDescription>
            Configure policy thresholds and review automated action audit history.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="settings" className="flex flex-col min-h-0 flex-1">
          <TabsList className="w-full shrink-0 grid grid-cols-2">
            <TabsTrigger value="settings">Settings</TabsTrigger>
            <TabsTrigger value="logs">Logs</TabsTrigger>
          </TabsList>

          <TabsContent value="settings" className="mt-4 overflow-y-auto max-h-[calc(85vh-10rem)]">
            <PlanningAutomationPanel
              embedded
              policies={policies}
              loading={policiesLoading}
              onChange={onPolicyChange}
              onSave={onSavePolicy}
              savingPolicyType={savingPolicyType}
            />
          </TabsContent>

          <TabsContent value="logs" className="mt-4 overflow-y-auto max-h-[calc(85vh-10rem)]">
            <PlanningAuditLogPanel embedded logs={auditLogs} loading={auditLoading} />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
