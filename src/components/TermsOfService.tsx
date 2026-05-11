import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';

interface TermsOfServiceProps {
  onBack: () => void;
}

export const TermsOfService = ({ onBack }: TermsOfServiceProps) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="container mx-auto px-6 py-8">
        <Button 
          variant="ghost" 
          onClick={onBack}
          className="mb-6 flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Button>
        
        <Card className="max-w-4xl mx-auto bg-white">
          <CardHeader>
            <CardTitle className="text-3xl font-bold text-center">Terms of Service</CardTitle>
            <p className="text-center text-slate-600">Last updated September 22, 2025</p>
          </CardHeader>
          <CardContent className="prose prose-slate max-w-none space-y-6">
            <div>
              <h2 className="text-2xl font-semibold mb-4">AGREEMENT TO OUR LEGAL TERMS</h2>
              <p className="text-slate-700 leading-relaxed">
                We are Catchalyze ("<strong>Company</strong>," "<strong>we</strong>," "<strong>us</strong>," "<strong>our</strong>"), a company registered in California, United States at 2580 California St, Apt 2333, Mountain View, CA 94040.
              </p>
              <p className="text-slate-700 leading-relaxed">
                We operate the website app.catchalyze.com (the "<strong>Site</strong>"), as well as any other related products and services that refer or link to these legal terms (the "<strong>Legal Terms</strong>") (collectively, the "<strong>Services</strong>").
              </p>
              <p className="text-slate-700 leading-relaxed">
                Catchalyze is a customer intelligence platform that monitors customer interactions across support channels (Slack, Zendesk) to automatically detect emerging issues and trends in real-time. The software provides early warning alerts, sentiment analysis, and actionable insights to help customer success teams prevent issues from escalating and impacting customer retention.
              </p>
              <p className="text-slate-700 leading-relaxed">
                You can contact us by phone at 7863027813, email at <a href="mailto:support@catchalyze.com" className="text-blue-600 hover:underline">support@catchalyze.com</a>, or by mail to 2580 California St, Apt 2333, Mountain View, CA 94040, United States.
              </p>
              <p className="text-slate-700 leading-relaxed">
                These Legal Terms constitute a legally binding agreement made between you, whether personally or on behalf of an entity ("<strong>you</strong>"), and Catchalyze, concerning your access to and use of the Services. You agree that by accessing the Services, you have read, understood, and agreed to be bound by all of these Legal Terms. <strong>IF YOU DO NOT AGREE WITH ALL OF THESE LEGAL TERMS, THEN YOU ARE EXPRESSLY PROHIBITED FROM USING THE SERVICES AND YOU MUST DISCONTINUE USE IMMEDIATELY.</strong>
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">1. OUR SERVICES</h2>
              <p className="text-slate-700 leading-relaxed">
                The information provided when using the Services is not intended for distribution to or use by any person or entity in any jurisdiction or country where such distribution or use would be contrary to law or regulation or which would subject us to any registration requirement within such jurisdiction or country.
              </p>
              <p className="text-slate-700 leading-relaxed">
                Accordingly, those persons who choose to access the Services from other locations do so on their own initiative and are solely responsible for compliance with local laws, if and to the extent local laws are applicable.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">2. INTELLECTUAL PROPERTY RIGHTS</h2>
              <p className="text-slate-700 leading-relaxed">
                We are the owner or the licensee of all intellectual property rights in our Services, including all source code, databases, functionality, software, website designs, audio, video, text, photographs, and graphics in the Services (collectively, the "<strong>Content</strong>"), as well as the trademarks, service marks, and logos contained therein (the "<strong>Marks</strong>").
              </p>
              <p className="text-slate-700 leading-relaxed">
                Our Content and Marks are protected by copyright and trademark laws (and various other intellectual property rights and unfair competition laws) and treaties in the United States and around the world.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">3. USER REPRESENTATIONS</h2>
              <p className="text-slate-700 leading-relaxed">
                By using the Services, you represent and warrant that: (1) you have the legal capacity and you agree to comply with these Legal Terms; (2) you are not under the age of 13; (3) you are not a minor in the jurisdiction in which you reside; (4) you will not access the Services through automated or non-human means; (5) you will not use the Services for any illegal or unauthorized purpose; and (6) your use of the Services will not violate any applicable law or regulation.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">4. PROHIBITED ACTIVITIES</h2>
              <p className="text-slate-700 leading-relaxed">
                You may not access or use the Services for any purpose other than that for which we make the Services available. The Services may not be used in connection with any commercial endeavors except those that are specifically endorsed or approved by us.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">5. CONTRIBUTION LICENSE</h2>
              <p className="text-slate-700 leading-relaxed">
                You and Services agree that we may access, store, process, and use any information and personal data that you provide and your choices (including settings).
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">6. SUBMISSIONS</h2>
              <p className="text-slate-700 leading-relaxed">
                You acknowledge and agree that any questions, comments, suggestions, ideas, feedback, or other information regarding the Services ("<strong>Submissions</strong>") provided by you to us are non-confidential and shall become our sole property.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">7. PRIVACY POLICY</h2>
              <p className="text-slate-700 leading-relaxed">
                We care about data privacy and security. Please review our Privacy Policy, which also governs your use of the Services, to understand our practices.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">8. TERMINATION</h2>
              <p className="text-slate-700 leading-relaxed">
                We may terminate or suspend your account and bar access to the Services immediately, without prior notice or liability, under our sole discretion, for any reason whatsoever and without limitation, including but not limited to a breach of the Terms.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">9. DISCLAIMER</h2>
              <p className="text-slate-700 leading-relaxed">
                THE INFORMATION ON THIS WEBSITE IS PROVIDED ON AN "AS IS" BASIS. TO THE FULLEST EXTENT PERMITTED BY LAW, THIS COMPANY EXCLUDES ALL REPRESENTATIONS, WARRANTIES, CONDITIONS, UNDERTAKINGS, AND ALL OTHER TERMS OF ANY KIND, WHETHER EXPRESS OR IMPLIED, STATUTORY OR OTHERWISE.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">10. LIMITATIONS OF LIABILITY</h2>
              <p className="text-slate-700 leading-relaxed">
                IN NO EVENT WILL WE OR OUR DIRECTORS, EMPLOYEES, OR AGENTS BE LIABLE TO YOU OR ANY THIRD PARTY FOR ANY DIRECT, INDIRECT, CONSEQUENTIAL, EXEMPLARY, INCIDENTAL, SPECIAL, OR PUNITIVE DAMAGES, INCLUDING LOST PROFIT, LOST REVENUE, LOSS OF DATA, OR OTHER DAMAGES ARISING FROM YOUR USE OF THE SERVICES.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">11. GOVERNING LAW</h2>
              <p className="text-slate-700 leading-relaxed">
                These Legal Terms shall be governed by and defined following the laws of California. Catchalyze and yourself irrevocably consent that the courts of California shall have exclusive jurisdiction to resolve any dispute which may arise in connection with these Legal Terms.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">12. REFUNDS AND CANCELLATIONS</h2>
              <p className="text-slate-700 leading-relaxed">
                We offer a 30-day money-back guarantee from the date of payment. Refund requests must be submitted via email to support@catchalyze.com. Refunds will be processed within 5-7 business days to the original payment method. After 30 days, all sales are final. Account access terminates immediately upon refund processing.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">13. CHANGES TO THESE LEGAL TERMS</h2>
              <p className="text-slate-700 leading-relaxed">
                We reserve the right, in our sole discretion, to make changes or modifications to these Legal Terms from time to time. We will alert you about any changes by updating the "Last updated" date of these Legal Terms, and you waive any right to receive specific notice of each such change.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-semibold mb-4">14. CONTACT US</h2>
              <p className="text-slate-700 leading-relaxed">
                In order to resolve a complaint regarding the Services or to receive further information regarding use of the Services, please contact us at:
              </p>
              <div className="bg-slate-50 p-4 rounded-lg mt-4">
                <p className="font-medium">Catchalyze</p>
                <p>2580 California St, Apt 2333</p>
                <p>Mountain View, CA 94040</p>
                <p>United States</p>
                <p>Email: <a href="mailto:support@catchalyze.com" className="text-blue-600 hover:underline">support@catchalyze.com</a></p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};