import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';

interface PrivacyPolicyProps {
  children: React.ReactNode;
}

export const PrivacyPolicy = ({ children }: PrivacyPolicyProps) => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Privacy Policy</DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-[60vh] pr-4">
          <div className="space-y-6 text-sm">
            <p><strong>Last updated September 22, 2025</strong></p>
            
            <p>This Privacy Notice for Catchalyze ("<strong>we</strong>," "<strong>us</strong>," or "<strong>our</strong>"), describes how and why we might access, collect, store, use, and/or share ("<strong>process</strong>") your personal information when you use our services ("<strong>Services</strong>"), including when you:</p>
            
            <ul>
              <li>Visit our website at <a href="https://app.catchalyze.com" className="text-blue-600 hover:underline">https://app.catchalyze.com</a> or any website of ours that links to this Privacy Notice</li>
              <li>Use Catchalyze. Catchalyze is a customer intelligence platform that monitors customer interactions across support channels (Slack, Zendesk) to automatically detect emerging issues and trends in real-time. The software provides early warning alerts, sentiment analysis, and actionable insights to help customer success teams prevent issues from escalating and impacting customer retention</li>
              <li>Engage with us in other related ways, including any sales, marketing, or events</li>
            </ul>
            
            <p><strong>Questions or concerns?</strong> Reading this Privacy Notice will help you understand your privacy rights and choices. We are responsible for making decisions about how your personal information is processed. If you do not agree with our policies and practices, please do not use our Services. If you still have any questions or concerns, please contact us at <a href="mailto:support@catchalyze.com" className="text-blue-600 hover:underline">support@catchalyze.com</a>.</p>
            
            <h2><strong>SUMMARY OF KEY POINTS</strong></h2>
            
            <p><em>This summary provides key points from our Privacy Notice, but you can find out more details about any of these topics by reading the full policy.</em></p>
            
            <p><strong>What personal information do we process?</strong> When you visit, use, or navigate our Services, we may process personal information depending on how you interact with us and the Services, the choices you make, and the products and features you use.</p>
            
            <p><strong>Do we process any sensitive personal information?</strong> We do not process sensitive personal information.</p>
            
            <p><strong>Do we collect any information from third parties?</strong> We may collect information from public databases, marketing partners, social media platforms, and other outside sources.</p>
            
            <p><strong>How do we process your information?</strong> We process your information to provide, improve, and administer our Services, communicate with you, for security and fraud prevention, and to comply with law. We may also process your information for other purposes with your consent.</p>
            
            <p><strong>In what situations and with which parties do we share personal information?</strong> We may share information in specific situations and with specific third parties.</p>
            
            <p><strong>How do we keep your information safe?</strong> We have adequate organizational and technical processes and procedures in place to protect your personal information. However, no electronic transmission over the internet or information storage technology can be guaranteed to be 100% secure, so we cannot promise or guarantee that hackers, cybercriminals, or other unauthorized third parties will not be able to defeat our security and improperly collect, access, steal, or modify your information.</p>
            
            <p><strong>What are your rights?</strong> Depending on where you are located geographically, the applicable privacy law may mean you have certain rights regarding your personal information.</p>
            
            <p><strong>How do you exercise your rights?</strong> The easiest way to exercise your rights is by contacting us at <a href="mailto:support@catchalyze.com" className="text-blue-600 hover:underline">support@catchalyze.com</a> or by mail to:</p>
            
            <div className="bg-slate-50 p-4 rounded-lg my-4">
              <p className="font-medium">Catchalyze</p>
              <p>2580 California St, Apt 2333</p>
              <p>Mountain View, CA 94040</p>
              <p>United States</p>
            </div>
            
            <p>We will consider and act upon any request in accordance with applicable data protection laws.</p>
            
            <h2><strong>TABLE OF CONTENTS</strong></h2>
            <ol>
              <li>WHAT INFORMATION DO WE COLLECT?</li>
              <li>HOW DO WE PROCESS YOUR INFORMATION?</li>
              <li>WHAT LEGAL BASES DO WE RELY ON TO PROCESS YOUR PERSONAL INFORMATION?</li>
              <li>WHEN AND WITH WHOM DO WE SHARE YOUR PERSONAL INFORMATION?</li>
              <li>DO WE USE COOKIES AND OTHER TRACKING TECHNOLOGIES?</li>
              <li>HOW LONG DO WE KEEP YOUR INFORMATION?</li>
              <li>HOW DO WE KEEP YOUR INFORMATION SAFE?</li>
              <li>DO WE COLLECT INFORMATION FROM MINORS?</li>
              <li>WHAT ARE YOUR PRIVACY RIGHTS?</li>
              <li>CONTROLS FOR DO-NOT-TRACK FEATURES</li>
              <li>DO UNITED STATES RESIDENTS HAVE SPECIFIC PRIVACY RIGHTS?</li>
              <li>DO WE MAKE UPDATES TO THIS NOTICE?</li>
              <li>HOW CAN YOU CONTACT US ABOUT THIS NOTICE?</li>
              <li>HOW CAN YOU REVIEW, UPDATE, OR DELETE THE DATA WE COLLECT FROM YOU?</li>
            </ol>
            
            <p>For the complete privacy policy with all detailed sections, please visit our website or contact us directly.</p>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};