import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface CookiePolicyProps {
  children: React.ReactNode;
}

export const CookiePolicy = ({ children }: CookiePolicyProps) => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Cookie Policy</DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-[60vh] pr-4">
          <div className="space-y-6 text-sm">
            <div>
              <h1 className="text-2xl font-bold mb-4">COOKIE POLICY</h1>
              <p className="font-semibold mb-4">Last updated September 22, 2025</p>
              
              <p className="mb-4">
                This Cookie Policy explains how Catchalyze ("<strong>Company</strong>," "<strong>we</strong>," "<strong>us</strong>," and "<strong>our</strong>") uses cookies and similar technologies to recognize you when you visit our website at <a href="https://app.catchalyze.com" className="text-blue-600 hover:underline">https://app.catchalyze.com</a> ("<strong>Website</strong>"). It explains what these technologies are and why we use them, as well as your rights to control our use of them.
              </p>
              
              <p className="mb-6">
                In some cases we may use cookies to collect personal information, or that becomes personal information if we combine it with other information.
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">What are cookies?</h2>
              <p className="mb-4">
                Cookies are small data files that are placed on your computer or mobile device when you visit a website. Cookies are widely used by website owners in order to make their websites work, or to work more efficiently, as well as to provide reporting information.
              </p>
              <p className="mb-4">
                Cookies set by the website owner (in this case, Catchalyze) are called "first-party cookies." Cookies set by parties other than the website owner are called "third-party cookies." Third-party cookies enable third-party features or functionality to be provided on or through the website (e.g., advertising, interactive content, and analytics). The parties that set these third-party cookies can recognize your computer both when it visits the website in question and also when it visits certain other websites.
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">Why do we use cookies?</h2>
              <p className="mb-4">
                We use first- and third-party cookies for several reasons. Some cookies are required for technical reasons in order for our Website to operate, and we refer to these as "essential" or "strictly necessary" cookies. Other cookies also enable us to track and target the interests of our users to enhance the experience on our Online Properties. Third parties serve cookies through our Website for advertising, analytics, and other purposes. This is described in more detail below.
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">How can I control cookies?</h2>
              <p className="mb-4">
                You have the right to decide whether to accept or reject cookies. You can exercise your cookie rights by setting your preferences in the Cookie Consent Manager. The Cookie Consent Manager allows you to select which categories of cookies you accept or reject. Essential cookies cannot be rejected as they are strictly necessary to provide you with services.
              </p>
              <p className="mb-4">
                The Cookie Consent Manager can be found in the notification banner and on our website. If you choose to reject cookies, you may still use our website though your access to some functionality and areas of our website may be restricted. You may also set or amend your web browser controls to accept or refuse cookies.
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">The specific types of first- and third-party cookies served through our Website and the purposes they perform are described in the table below:</h2>
              
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Essential website cookies:</h3>
                <p className="mb-2">
                  These cookies are strictly necessary to provide you with services available through our Website and to use some of its features, such as access to secure areas.
                </p>
              </div>

              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Performance and functionality cookies:</h3>
                <p className="mb-2">
                  These cookies are used to enhance the performance and functionality of our Website but are non-essential to their use. However, without these cookies, certain functionality (like videos) may become unavailable.
                </p>
              </div>

              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Analytics and customization cookies:</h3>
                <p className="mb-2">
                  These cookies collect information that is used either in aggregate form to help us understand how our Website is being used or how effective our marketing campaigns are, or to help us customize our Website for you.
                </p>
              </div>

              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Advertising cookies:</h3>
                <p className="mb-2">
                  These cookies are used to make advertising messages more relevant to you. They perform functions like preventing the same ad from continuously reappearing, ensuring that ads are properly displayed for advertisers, and in some cases selecting advertisements that are based on your interests.
                </p>
              </div>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">What about other tracking technologies, like web beacons?</h2>
              <p className="mb-4">
                Cookies are not the only way to recognize or track visitors to a website. We may use other, similar technologies from time to time, like web beacons (sometimes called "tracking pixels" or "clear gifs"). These are tiny graphics files that contain a unique identifier that enables us to recognize when someone has visited our Website or opened an email including them. This allows us, for example, to monitor the traffic patterns of users from one page within a website to another, to deliver or communicate with cookies, to understand whether you have come to the website from an online advertisement displayed on a third-party website, to improve site performance, and to measure the success of email marketing campaigns. In many instances, these technologies are reliant on cookies to function properly, and so declining cookies will impair their functioning.
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">Do you use Flash cookies or Local Shared Objects?</h2>
              <p className="mb-4">
                Websites may also use so-called "Flash Cookies" (also known as Local Shared Objects or "LSOs") to, among other things, collect and store information about your use of our services, fraud prevention, and for other site operations.
              </p>
              <p className="mb-4">
                If you do not want Flash Cookies stored on your computer, you can adjust the settings of your Flash player to block Flash Cookies storage using the tools contained in the <a href="#" className="text-blue-600 hover:underline">Website Storage Settings Panel</a>. You can also control Flash Cookies by going to the <a href="#" className="text-blue-600 hover:underline">Global Storage Settings Panel</a> and following the instructions (which may include instructions that explain, for example, how to delete existing Flash Cookies (referred to "information" on the Macromedia site), how to prevent Flash LSOs from being placed on your computer without your being asked, and (for Flash Player 8 and later) how to block Flash Cookies that are not being delivered by the operator of the page you are on at the time).
              </p>
              <p className="mb-4">
                Please note that setting the Flash Player to restrict or limit acceptance of Flash Cookies may reduce or impede the functionality of some Flash applications, including, potentially, Flash applications used in connection with our services or online content.
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">Do you serve targeted advertising?</h2>
              <p className="mb-4">
                Third parties may serve cookies on your computer or mobile device to serve advertising through our Website. These companies may use information about your visits to this and other websites in order to provide relevant advertisements about goods and services that you may be interested in. They may also employ technology that is used to measure the effectiveness of advertisements. They can accomplish this by using cookies or web beacons to collect information about your visits to this and other sites in order to provide relevant advertisements about goods and services of potential interest to you. The information collected through this process does not enable us or them to identify your name, contact details, or other details that directly identify you unless you choose to provide these.
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">How often will you update this Cookie Policy?</h2>
              <p className="mb-4">
                We may update this Cookie Policy from time to time in order to reflect, for example, changes to the cookies we use or for other operational, legal, or regulatory reasons. Please therefore revisit this Cookie Policy regularly to stay informed about our use of cookies and related technologies.
              </p>
              <p className="mb-4">
                The date at the top of this Cookie Policy indicates when it was last updated.
              </p>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">Where can I get further information?</h2>
              <p className="mb-4">
                If you have any questions about our use of cookies or other technologies, please email us at <a href="mailto:support@catchalyze.com" className="text-blue-600 hover:underline">support@catchalyze.com</a> or by post to:
              </p>
              <div className="ml-4 mb-4">
                <p>Catchalyze</p>
                <p>2580 California St, Apt 2333</p>
                <p>Mountain View, CA 94040</p>
                <p>United States</p>
                <p>Phone: 7863027813</p>
              </div>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};